
# ResumeAuthorizationPolicy Specification (v1.0)

## 1. Executive Summary

`ResumeAuthorizationPolicy` defines how Flotilla determines whether a decoded `ResumeTokenPayload` is authorized to resume a suspended execution phase.

ResumeAuthorizationPolicy:

-   Is injectable    
-   Is stateless
-   Is deterministic
-   Is side-effect free
-   Returns a boolean decision only
    
It does not:

-   Issue ResumeToken
-   Modify durable state
-   Perform durable mutations
-   Enforce authentication mechanisms
-   Define identity systems
-   Produce user-facing error messages
    
It evaluates whether the decoded resume token payload is authorized to resume the specific `SuspendEntry`.

## 2. Architectural Context

ResumeAuthorizationPolicy collaborates with:

-   `FlotillaRuntime`
-   `ResumeTokenPayload`
-   `SuspendEntry`
    
It is invoked only during resume validation.

It operates after:

-   ResumeToken integrity validation
-   SuspendEntry identification
-   Durable state validation
    
It does not access storage directly.
It does not mutate state.

## 3. Core Concepts

`ResumeAuthorizationPolicy` is a stateless policy object that decides whether a decoded resume token payload is permitted to resume a specific durable `SuspendEntry`.

Core inputs:

- `ResumeTokenPayload` decoded from the supplied resume token.
- Durable `SuspendEntry` identified by resume-token validation.

The policy returns only a boolean authorization decision.

----------

## 4. Responsibilities

ResumeAuthorizationPolicy is responsible for:

-   Determining whether a given `ResumeTokenPayload` is permitted to resume a specific `SuspendEntry`.

----------

## 5. Non-Responsibilities

ResumeAuthorizationPolicy is NOT responsible for:

-   Validating ResumeToken cryptographic integrity
-   Checking suspend consumption state
-   Issuing ResumeToken
-   Appending ThreadEntry
-   Producing error responses
-   Enforcing broader authentication mechanisms
    
Durable lifecycle enforcement remains owned by `FlotillaRuntime`.

----------

## 6. Behavioral Contract

### Interface Contract

```python
class  ResumeAuthorizationPolicy(Protocol):  
  
  async def  is_authorized(
  self,  
  *,  
  payload: ResumeTokenPayload,
  suspend_entry: SuspendEntry,  
 ) -> bool:  
 ```

### Parameter Semantics

| Field | Type | Notes |
|--|--|--|
| `payload` | `ResumeTokenPayload` | Decoded resume token payload |
| `suspend_entry` | `SuspendEntry` | The durable suspend entry associated with the resume_token |

The policy MUST return:

-   `True` → resume allowed
    
-   `False` → resume denied

### Evaluation Semantics

During resume handling, FlotillaRuntime MUST:

1.  Validate ResumeToken integrity and suspend state.
2.  Identify the correct `SuspendEntry`.
3.  Invoke:
```python
is_authorized(payload=payload, suspend_entry=suspend_entry)
```
5.  If the result is `False`, reject the resume attempt.
6.  If the result is `True`, proceed with resume.
    
ResumeToken ownership alone MUST NOT be sufficient for resume if the policy denies authorization.

### Non-Fatal Requirement

ResumeAuthorizationPolicy MUST NOT cause runtime execution to fail due to internal errors.

If a policy raises an unexpected exception, the runtime MAY defensively treat the resume as unauthorized.

Policy failure MUST NOT corrupt runtime state.

----------

## 7. Constraints & Guarantees

ResumeAuthorizationPolicy MUST:

1.  Be pure and side-effect free.
2.  Not mutate `ResumeTokenPayload`.
3.  Not mutate `SuspendEntry`.
4.  Not perform durable mutations.
5.  Return identical results for identical inputs.
6.  Be safe for concurrent invocation.
    
ResumeAuthorizationPolicy MUST NOT:

-   Access `ThreadEntryStore` directly.
-   Modify durable thread state.
-   Trigger lifecycle transitions.
-   Raise uncaught exceptions.

----------

### Thread Safety

Implementations MUST:

-   Be stateless or safely immutable.
-   Be thread-safe.
-   Be re-entrant.

----------

## 8. Configuration Contract

Flotilla MAY provide a permissive default:

```python
class  AllowAllResumeAuthorizationPolicy:  
  
  def  is_authorized(self, *, payload, suspend_entry):
  return  True
```
This allows applications that enforce authorization upstream to opt out of additional checks.

----------

### Architectural Guarantees

This specification guarantees:

-   Resume authorization is enforced at runtime boundary
-   Flotilla does not become a security framework
-   Authorization semantics remain application-defined
-   Token possession alone is insufficient for resume
-   Security enforcement is minimal and composable

## 9. Related Specifications

- `FlotillaRuntime`
- `Runtime I/O`
- `Thread Model`
- `ResumeToken`
