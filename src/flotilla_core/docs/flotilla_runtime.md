# FlotillaRuntime Specification (v1.4-draft)

## 1. Executive Summary

FlotillaRuntime is a stateless orchestration kernel that:

- Is the entry point for user execution requests
- Initiates execution phases by appending `UserInput` or `ResumeEntry`
- Invokes `OrchestrationStrategy` to obtain canonical `AgentEvent`
- Appends terminal entries (`AgentOutput`, `SuspendEntry`, `ErrorEntry`)
- Issues `ResumeToken`s on suspend
- Enforces thread-scoped concurrency via CAS
- Enforces lazy timeout closure of orphaned phases
- Emits user-facing results via `RuntimeResponse` (sync) or `RuntimeEvent` (streaming)
- Enforces resume authorization via injected ResumeAuthorizationPolicy

### Out of Scope

Runtime MUST NOT:

- Create threads (thread identity lifecycle is outside runtime)
- Construct `ExecutionConfig` (built outside runtime)
- Persist tool semantics or tool-specific records
- Guarantee delivery of external notifications (`SuspendPolicy` reliability is app-specific)

---

## 2. System Architecture Context

Runtime sits between:

- Transport (HTTP/SSE/WS/CLI) and the durable thread log
- `OrchestrationStrategy` / `FlotillaAgent` producing `AgentEvent`
- `ThreadEntryStore` enforcing CAS + persistence
- Policies (`SuspendPolicy`, `TelemetryPolicy`, `ExecutionTimeoutPolicy`)

Thread status determination is owned by `ThreadContext`, not runtime.

---

## 3. Required Collaborators

### 3.1 ThreadEntryStore (Required)

Runtime MUST use `ThreadEntryStore` to:

- Load thread entries
- Append entries with predicates
- Rely on store-assigned `entry_id` + timestamp

Runtime MUST treat `ThreadEntryStore` as authoritative. Runtime MUST raise a runtime error if thread does not exist.

### 3.2 ExecutionConfig (Required Input)

Runtime MUST receive `ExecutionConfig` as input. `ExecutionConfig` MUST be constructed outside runtime (typically via `ExecutionConfigService` from `FlotillaApplication`). Runtime MUST NOT construct `ExecutionConfig`.

### 3.3 OrchestrationStrategy (Required)

Runtime MUST invoke OrchestrationStrategy with the reconstructed ThreadContext and the provided immutable ExecutionConfig.

OrchestrationStrategy defines how a single execution phase proceeds. It may coordinate one or more FlotillaAgent or nested OrchestrationStrategy instances, including multi-agent workflows and ephemeral inter-agent data passing. All such coordination occurs within the phase and does not modify durable thread state.

OrchestrationStrategy MUST yield only canonical AgentEvent and MUST yield exactly one terminal AgentEvent per invocation. Execution failures MUST be represented as AgentEvent.error rather than raised exceptions.

Runtime treats OrchestrationStrategy as an execution engine and lifecycle-neutral producer of AgentEvent. Durable mutation and lifecycle enforcement remain exclusively owned by FlotillaRuntime.

For full behavioral rules, see the OrchestrationStrategy Specification.

### 3.4 SuspendPolicy (Required)

Runtime MUST invoke SuspendPolicy synchronously after durably appending a SuspendEntry.

SuspendPolicy is responsible for any external side-effects triggered by suspension (e.g., notifications, callbacks, or workflow signaling). It does not participate in lifecycle enforcement or durable mutation.

Failure of SuspendPolicy MUST be non-fatal and MUST NOT affect execution state or resume semantics.

For full behavioral rules, see the SuspendPolicy Specification.

### 3.5 TelemetryPolicy (Optional)

Runtime MAY invoke TelemetryPolicy to emit execution telemetry events at defined lifecycle points.

TelemetryPolicy is observational only. It MUST NOT mutate durable state, influence execution flow, or affect determinism.

Failure of TelemetryPolicy MUST be non-fatal.

For full behavioral rules, see the TelemetryPolicy Specification.

### 3.6 ExecutionTimeoutPolicy (Required)

Runtime MUST invoke ExecutionTimeoutPolicy to determine whether an active execution phase has exceeded its timeout duration.

The policy evaluates expiration based on durable thread state and returns a boolean decision only. It does not enforce timeout directly or perform durable mutation.

Timeout enforcement remains owned by FlotillaRuntime.

For full behavioral rules, see the ExecutionTimeoutPolicy Specification.

### 3.7 ResumeAuthorizationPolicy (Required)

Runtime MUST invoke `ResumeAuthorizationPolicy` during resume validation.

Runtime MUST:
1.  Validate ResumeToken integrity and suspend state.
2.  Load the associated `SuspendEntry`.
3.  Invoke:
    
```python
resume_authorization_policy.is_authorized(  
  request=request,  
  suspend_entry=suspend_entry  
)
```

If the policy returns `False`, runtime MUST reject the resume attempt.

ResumeToken possession alone MUST NOT be sufficient for resume when the policy denies authorization.

ResumeAuthorizationPolicy MUST NOT perform durable mutations.

---

## 4. Durable Reload Rule (REQUIRED)

After any successful `ThreadEntryStore.append()` call, runtime MUST:

1. Call `ThreadEntryStore.load(thread_id)`
2. Reconstruct a new `ThreadContext`
3. Proceed using only that reconstructed context

Runtime MUST NOT proceed using an in-memory assumed thread state after append.

---

## 5. Behavioral Contract

### 5.1 Thread Existence

On receiving a `RuntimeRequest`:

- Runtime MUST call `store.load(thread_id)`.
- If the thread does not exist, runtime MUST raise/emit `THREAD_NOT_FOUND`.
- Runtime MUST NOT attempt to create the thread.

### 5.2 Phase Initiation

Runtime MUST:

- Load and construct `ThreadContext`
- If an active phase exists, apply lazy timeout enforcement (§5.3)
- Append initiating entry using:
  - `expected_last_entry_id=<current_last_entry_id>` for non-empty threads
  - `expected_last_entry_id=None` for empty threads

If `append` returns `None`:
- Emit `CONCURRENT_EXECUTION_PHASE_NOT_ALLOWED`
- No durable mutation occurs

If `append` succeeds:
- MUST reload and reconstruct `ThreadContext`
- MUST invoke `OrchestrationStrategy`

### 5.2.1 Resume Handling (NEW)

If `RuntimeRequest.resume_token` is present:

Runtime MUST:

1.  Validate ResumeToken integrity (signature / lookup / expiry).
2.  Validate that:
   
    -   `thread_id` matches     
    -   `runtime_key` matches
    -   referenced `SuspendEntry` exists
    -   referenced suspend has no terminal child
        
3.  Invoke `ResumeAuthorizationPolicy`.
4.  If authorization fails, reject resume.
5.  Append `ResumeEntry` referencing the `SuspendEntry`.
6.  Reload thread (Durable Reload Rule).
7.  Invoke `OrchestrationStrategy`.
    
Resume MUST NOT proceed without successful authorization.

### 5.3 Lazy Timeout Enforcement

If `ThreadContext` indicates an active phase and `now - initiating_entry.timestamp > timeout_duration`, then runtime MUST:

- Attempt to append `ErrorEntry(EXECUTION_TIMEOUT)` using `expected_last_entry_id=<current_last_entry_id>`
- On success: MUST reload and proceed
- On predicate failure: MUST reload and re-evaluate

No background tasks are permitted. Timeout is derived solely from store timestamps.

### 5.4 Phase Termination

When `OrchestrationStrategy` yields a terminal `AgentEvent`:

- Runtime MUST map it to exactly one terminal `ThreadEntry`.
- Runtime MUST append terminal entry with `require_no_terminal_for_parent=<parent_entry_id>`.

On predicate failure (`None`):
- Runtime MUST reload thread
- Runtime MUST treat as duplicate-terminal conflict (runtime policy may decide whether to surface as error or treat as idempotent duplicate)

On success:
- MUST reload thread
- MUST emit response

When appending SuspendEntry, runtime MUST persist any resume_audience value included by the agent or orchestration strategy without interpretation.

Runtime MUST treat resume_audience as opaque.

---

## 6. Thread-Scoped Concurrency

Runtime guarantees concurrency only within a `thread_id`. Runtime does not prevent duplicates across multiple threads. Cross-thread idempotency is an application responsibility.

---

## 7. Crash Recovery

If the process crashes mid-phase and no terminal entry exists, runtime resolves the misalignment only via lazy timeout closure. Runtime provides phase-level recovery only. Tool-level recovery and step-level replay are out of scope.

---

## 8. Related Specifications

Only specifications that interact with `FlotillaRuntime`:

- ThreadEntryStore
- OrchestrationStrategy
- Thread Model (`ThreadEntry` / `ThreadContext`)
- AgentEvent
- ContentPart
- ResumeAuthorizationPolicy Specification