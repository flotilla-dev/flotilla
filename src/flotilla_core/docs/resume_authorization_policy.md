
# ResumeAuthorizationPolicy Specification (v1.0)

----------

## 1️⃣ Executive Summary

`ResumeAuthorizationPolicy` defines how Flotilla determines whether a `RuntimeRequest` is authorized to resume a suspended execution phase.

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
    
It evaluates whether the provided request is authorized to resume the specific `SuspendEntry`.

----------

## 2️⃣ Architectural Context

ResumeAuthorizationPolicy collaborates with:

-   `FlotillaRuntime`
-   `RuntimeRequest`
-   `SuspendEntry`
    
It is invoked only during resume validation.

It operates after:

-   ResumeToken integrity validation
-   SuspendEntry identification
-   Durable state validation
    
It does not access storage directly.
It does not mutate state.

----------

## 3️⃣ Responsibilities

ResumeAuthorizationPolicy is responsible for:

-   Determining whether a given `RuntimeRequest` is permitted to resume a specific `SuspendEntry`.

ResumeAuthorizationPolicy is NOT responsible for:

-   Validating ResumeToken cryptographic integrity
-   Checking suspend consumption state
-   Issuing ResumeToken
-   Appending ThreadEntry
-   Producing error responses
-   Enforcing broader authentication mechanisms
    
Durable lifecycle enforcement remains owned by `FlotillaRuntime`.

----------

## 4️⃣ Invariants

ResumeAuthorizationPolicy MUST:

1.  Be pure and side-effect free.
2.  Not mutate `RuntimeRequest`.
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

## 5️⃣ Interface Contract

```python
class  ResumeAuthorizationPolicy(Protocol):  
  
  def  is_authorized(  
  self,  
  *,  
  request: RuntimeRequest,  
  suspend_entry: SuspendEntry,  
 ) -> bool:  
 ```

### Parameter Semantics

| Field | Type | Notes |
|--|--|--|
| `request` | `RuntimeRequest` | The full resume request attempting to resume execution |
| `suspend_entry` | `SuspendEntry` | The durable suspend entry associated with the resume_token |

The policy MUST return:

-   `True` → resume allowed
    
-   `False` → resume denied
    

----------

## 6️⃣ Evaluation Semantics

During resume handling, FlotillaRuntime MUST:

1.  Validate ResumeToken integrity and suspend state.
2.  Identify the correct `SuspendEntry`.
3.  Invoke:
```python
is_authorized(request=request, suspend_entry=suspend_entry)
```
5.  If the result is `False`, reject the resume attempt.
6.  If the result is `True`, proceed with resume.
    
ResumeToken ownership alone MUST NOT be sufficient for resume if the policy denies authorization.

----------

## 7️⃣ Thread Safety

Implementations MUST:

-   Be stateless or safely immutable.
-   Be thread-safe.
-   Be re-entrant.
    
----------

## 8️⃣ Non-Fatal Requirement

ResumeAuthorizationPolicy MUST NOT cause runtime execution to fail due to internal errors.

If a policy raises an unexpected exception, the runtime MAY defensively treat the resume as unauthorized.

Policy failure MUST NOT corrupt runtime state.

----------

## 9️⃣ Default Implementation

Flotilla MAY provide a permissive default:

```python
class  AllowAllResumeAuthorizationPolicy:  
  
  def  is_authorized(self, *, request, suspend_entry):  
  return  True
```
This allows applications that enforce authorization upstream to opt out of additional checks.

----------

## 🔟 Architectural Guarantees

This specification guarantees:

-   Resume authorization is enforced at runtime boundary
-   Flotilla does not become a security framework
-   Authorization semantics remain application-defined
-   Token possession alone is insufficient for resume
-   Security enforcement is minimal and composable