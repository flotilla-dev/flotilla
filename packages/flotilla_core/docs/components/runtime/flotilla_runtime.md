# FlotillaRuntime Specification (v1.5-draft)

----------

## 1. Executive Summary

FlotillaRuntime is a stateless orchestration kernel that:

-   Serves as the entry point for user execution requests    
-   Constructs `PhaseContext` internally via `PhaseContextService`
-   Initiates execution phases by appending `UserInput` or `ResumeEntry`
-   Invokes `OrchestrationStrategy` to obtain canonical `AgentEvent`
-   Streams non-terminal events without durable mutation
-   Appends exactly one terminal entry per phase (`AgentOutput`, `SuspendEntry`, or `ErrorEntry`)
-   Issues `ResumeToken`s on suspend
-   Enforces thread-scoped concurrency via CAS
-   Enforces lazy timeout closure of orphaned phases
-   Emits user-facing results via `RuntimeResponse` (sync) or `RuntimeEvent` (streaming)
-   Validates and constructs resume flow via injected ResumeService    
-   Resume authorization is enforced indirectly through `ResumeService`, which may use `ResumeAuthorizationPolicy` internally.

### Out of Scope

Runtime MUST NOT:

-   Create threads (thread identity lifecycle is outside runtime)
-   Require callers to construct `PhaseContext`
-   Persist tool semantics or tool-specific records
-   Guarantee delivery of external notifications (SuspendPolicy reliability is app-specific)
    
----------

## 2. Architectural Context

Runtime sits between:

-   Transport (HTTP/SSE/WS/CLI) and the durable thread log
-   `OrchestrationStrategy` / `FlotillaAgent` producing `AgentEvent`
-   `ThreadEntryStore` enforcing CAS + persistence
-   Policies:
    
    -   `SuspendPolicy`    
    -   `TelemetryPolicy`
    -   `ExecutionTimeoutPolicy`
    -   `ResumeService`
        

Thread lifecycle state is derived exclusively from `ThreadContext`.

Runtime is stateless between requests.

----------

## 3. Core Concepts

`FlotillaRuntime` is the execution lifecycle coordinator. It consumes `RuntimeRequest`, drives orchestration, persists durable thread entries, and emits `RuntimeResponse` or `RuntimeEvent` output.

### Required Collaborators

### 3.1 ThreadEntryStore (Required)

Runtime MUST use `ThreadEntryStore` to:

-   Load thread entries
-   Append entries using CAS predicates
-   Rely on store-assigned `entry_id` and timestamps
    

Runtime MUST treat the store as authoritative.

If the thread does not exist, runtime MUST raise/emit `THREAD_NOT_FOUND`.

----------

### 3.2 PhaseContext (Required)

-   Runtime MUST construct a new immutable `PhaseContext` for each execution phase.
-   Runtime MUST obtain `PhaseContext` by invoking `PhaseContextService.create_phase_context(request)`.
-   `PhaseContext.phase_id` MUST be used as the `phase_id` for:
    -   The initiating `UserInput` or `ResumeEntry`
    -   All terminal entries appended for that phase.
        
-   Runtime and OrchestrationStrategy MUST treat `PhaseContext` as immutable
-   `agent_config` inside `PhaseContext` is adapter-defined and MUST be treated as opaque by runtime.
    
----------

### 3.3 OrchestrationStrategy (Required)

Runtime MUST invoke `OrchestrationStrategy` with:

-   Reconstructed `ThreadContext`
-   Immutable `PhaseContext`

`OrchestrationStrategy`:

-   MUST yield only canonical `AgentEvent`
-   MUST yield exactly one terminal `AgentEvent`
-   MUST represent failures as `AgentEvent.error`
-   MUST NOT perform durable mutations
-   MUST treat `PhaseContext` as opaque metadata/config
    
Runtime MUST defensively convert unexpected exceptions into a terminal `ErrorEntry`.

----------

### 3.4 SuspendPolicy (Configured)

Runtime accepts a `SuspendPolicy` collaborator and installs `NoOpSuspend` by default.

The current implementation does not invoke `SuspendPolicy.handle_suspend()` during suspend handling.

----------

### 3.5 ExecutionTimeoutPolicy (Required)

Runtime MUST invoke `ExecutionTimeoutPolicy` to determine whether an active phase has expired.

The policy returns a boolean only.

Timeout enforcement is owned exclusively by Runtime.

----------

### 3.6 ResumeService (Required)

Runtime MUST delegate resume handling to `ResumeService`.

`ResumeService` MUST be responsible for:

- Validating ResumeToken integrity
- Resolving and validating the referenced `SuspendEntry`
- Enforcing resume authorization
- Constructing the `ResumeEntry` when resume is allowed

Runtime MUST invoke `ResumeService` before appending any `ResumeEntry`.

If resume validation or authorization fails, Runtime MUST emit an error `RuntimeResponse/RuntimeEvent` and STOP.

`ResumeService` MUST NOT perform durable mutations directly.

----------

## 4. Responsibilities

`FlotillaRuntime` is responsible for:

- Validating runtime requests against durable thread state.
- Appending phase-initiating and terminal entries.
- Reloading durable state after each mutation.
- Driving `OrchestrationStrategy` execution.
- Mapping `AgentEvent` streams into runtime I/O.
- Enforcing suspend, resume, timeout, and terminal-state rules.

## 5. Non-Responsibilities

`FlotillaRuntime` is NOT responsible for:

- Implementing agent reasoning.
- Implementing tool behavior.
- Defining transport protocols.
- Persisting entries outside `ThreadEntryStore`.
- Defining application authentication or identity systems.
- Requiring telemetry for execution correctness.

----------

## 6. Behavioral Contract

### Durable Reload Rule (REQUIRED)

After any successful `ThreadEntryStore.append()` call, Runtime MUST:

1.  Call `ThreadEntryStore.load(thread_id)`
2.  Reconstruct a new `ThreadContext`
3.  Proceed using only the reconstructed context
   
Runtime MUST NOT rely on in-memory assumed state after append.

----------

### Canonical Execution Order

Upon receiving a `RuntimeRequest`, Runtime MUST execute the following steps:

----------

### Phase Initialization

1.  Receive `RuntimeRequest`. 
2.  Construct `PhaseContext` via `PhaseContextService`.
3.  Load durable thread state (`ThreadEntryStore.load()`).
4.  If last entry indicates an active phase:
    -   Invoke `ExecutionTimeoutPolicy`.
    -   If expired:
        -   Attempt to append `ErrorEntry(EXECUTION_TIMEOUT)` via CAS
        -   On success → durable reload.
        -   On predicate failure → durable reload and re-evaluate.
5. If `resume_token` is present
    - Invoke `ResumeService`.
    - `ResumeService` MUST validate ResumeToken integrity.
    - `ResumeService` MUST validate the referenced `SuspendEntry`.
    - `ResumeService` MUST enforce resume authorization.
    - If resume validation or authorization fails → emit error `RuntimeResponse/RuntimeEvent` and STOP.
6.  Construct initiating `ThreadEntry`:
    -   `UserInput` if no resume_token.
	-   `ResumeEntry` if resume_token.
    -   MUST include `phase_id = PhaseContext.phase_id`.
7.  Attempt CAS append of initiating entry.
    -   On predicate failure → emit `CONCURRENT_EXECUTION_PHASE_NOT_ALLOWED` error and STOP.
8.  Perform durable reload.
9.  Invoke `OrchestrationStrategy(thread_context, phase_context)`.
    
----------

### AgentEvent Handling

Runtime MUST process `AgentEvent` sequentially.

### Non-Terminal Events

For:

-   `message_start`
-   `message_chunk`
-   any other non-terminal events

Runtime MUST:

-   Emit `RuntimeEvent` (if streaming mode)
-   MUST NOT perform durable mutation

Streaming is ephemeral and not durable.

----------

### Terminal Events

Terminal events are:

-   `message_final`
-   `suspend`
-   `error`

Runtime MUST:

1.  Map terminal `AgentEvent` to exactly one terminal `ThreadEntry`.
2.  Attempt CAS append using:
```python
require_no_terminal_for_parent = initiating_entry_id
```    
3.  On predicate failure:
    -   Perform durable reload.
    -   Emit error `RuntimeResponse/RuntimeEvent` indicating terminal conflict.
    -   STOP.
        
4.  On success:
    -   Perform durable reload.
    -   If `SuspendEntry`, create a resume token.
    -   Emit final `RuntimeResponse` or terminal `RuntimeEvent`.
    -   STOP.
  
Runtime MUST NOT emit a terminal response before durable append succeeds.

----------

### Orchestration Exception Handling

If `OrchestrationStrategy` raises an unexpected exception:

Runtime MUST:

1.  Convert the exception into `ErrorEntry`  
2.  Attempt CAS append as a terminal entry.
3.  Perform durable reload.
4.  Emit error response.
5.  STOP.

No uncaught orchestration exception may leave a phase without terminal entry unless the process crashes.

----------

### Duplicate Terminal Handling

If CAS append of a terminal entry fails due to existing terminal:

Runtime MUST:

-   Perform durable reload.
-   Emit error `RuntimeResponse/RuntimeEvent` indicating duplicate terminal conflict.
-   STOP.

Runtime MUST NOT silently treat this as idempotent success.

----------

### Resume Semantics

Resume is treated as a new phase.

Resume MUST:

-   Be validated and authorized by `ResumeService`.
-   Produce a new `phase_id`.
-   Append a new `ResumeEntry`.
-   Follow identical orchestration flow.

----------

## 7. Constraints & Guarantees

### Thread-Scoped Concurrency

Concurrency guarantees apply only within a single `thread_id`.

Runtime does not prevent cross-thread duplication.

Cross-thread idempotency is application responsibility.

----------

### Crash Recovery

If a crash occurs mid-phase:

-   No terminal entry exists.
-   Runtime relies solely on lazy timeout enforcement on next invocation.
-   No background reconciliation is permitted.

Recovery operates strictly at phase level.

----------

## 8. Related Specifications

-   ThreadEntryStore
-   Thread Model (`ThreadEntry` / `ThreadContext`)
-   OrchestrationStrategy
-   AgentEvent
-   ContentPart
-   ResumeService
