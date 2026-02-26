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

Runtime MUST invoke `OrchestrationStrategy` with the reconstructed `ThreadContext` and provided `ExecutionConfig`. `OrchestrationStrategy` MUST yield only `AgentEvent` and MUST yield `AgentEvent.error` for failures (no raised execution errors).

### 3.4 SuspendPolicy (Required)

Runtime MUST invoke `SuspendPolicy` synchronously after durably appending `SuspendEntry`. `SuspendPolicy` failure MUST be non-fatal.

### 3.5 TelemetryPolicy (Optional)

Default no-op.

### 3.6 ExecutionTimeoutPolicy (Required)

Timeout enforcement is lazy and measured against the store-assigned timestamp of the most recent initiating entry.

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