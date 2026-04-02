# SuspendPolicy Specification (v1.2-draft)

## 1. Executive Summary

### Purpose

`SuspendPolicy` defines who should be notified and how when an execution phase terminates with a `SuspendEntry`.

`SuspendPolicy` is strictly post-terminal and non-mutating:

- `SuspendEntry` is authoritative and durable.
- `SuspendPolicy` does not affect thread state.
- `SuspendPolicy` failures are non-fatal.
- `SuspendPolicy` MUST NOT influence execution phase outcome.

`SuspendPolicy` exists to support multi-user environments where the resumer may differ from the requester.

### What SuspendPolicy Does

`SuspendPolicy`:

- Receives a durable `SuspendEntry`
- Receives the issued `ResumeToken`
- Performs synchronous best-effort routing or notification
- MAY emit advisory information (optional, non-authoritative)

### What SuspendPolicy Does Not Do

`SuspendPolicy` MUST NOT:

- Mutate durable state (no `ThreadEntryStore` writes)
- Create or modify `ResumeToken`
- Modify `ThreadContext`
- Determine thread status
- Alter execution outcome
- Influence terminal entry semantics

---

## 2. System Architecture Context

Execution order:

1. Runtime appends `SuspendEntry` durably.
2. Runtime reloads thread and reconstructs `ThreadContext`.
3. Runtime emits suspend response to the requester.
4. Runtime invokes `SuspendPolicy` synchronously (best-effort).

`SuspendPolicy` is invoked after durability and after terminal semantics are established. It cannot alter the canonical shape of the thread.

---

## 3. Canonical Interface

`SuspendPolicy` MUST expose semantics equivalent to:

```python
async def handle_suspend(
    thread_context: ThreadContext,
    suspend_entry: SuspendEntry,
    resume_token: ResumeToken,
    execution_config: ExecutionConfig,
) -> None:
    ...
```

### Input Requirements

- `thread_context` MUST reflect durable state after reload.
- `suspend_entry` MUST be the durable terminal entry for the phase.
- `resume_token` MUST correspond to that suspend entry.
- `execution_config` MUST match the configuration used for the phase.
- All inputs MUST be treated as immutable.

---

## 4. Behavioral Contract

### 4.1 Invocation Timing

Runtime MUST invoke `SuspendPolicy`:

- Only after `SuspendEntry` has been durably appended
- Only after reload of `ThreadContext`
- At most once per runtime request execution

Runtime MUST NOT invoke `SuspendPolicy` before durable mutation.

### 4.2 Synchronous, Non-Blocking Semantics

Runtime MUST await `SuspendPolicy` completion before exiting runtime execution. However:

- `SuspendPolicy` MUST NOT delay runtime completion indefinitely.
- Runtime SHOULD enforce a configurable timeout for `SuspendPolicy` execution.

### 4.3 Non-Mutating Guarantee

`SuspendPolicy` MUST NOT:

- Write to `ThreadEntryStore`
- Modify any `ThreadEntry`
- Append new entries
- Invalidate `ResumeToken`
- Alter `ThreadContext`

`SuspendPolicy` produces no durable mutations.

---

## 5. Error Handling Rules

`SuspendPolicy` MUST NOT allow errors to leak into runtime execution flow.

- Any exception raised by `SuspendPolicy` MUST be caught by `FlotillaRuntime`.
- Runtime MUST treat `SuspendPolicy` exceptions as non-fatal.

Runtime MUST NOT:

- Append additional `ThreadEntry`
- Convert policy failure into `ErrorEntry`
- Alter the terminal state of the execution phase
- Change the emitted suspend response

`SuspendPolicy` failures MUST NOT:

- Cause the execution phase to fail
- Modify thread state
- Invalidate `ResumeToken`
- Affect concurrency semantics

Runtime MAY log the error or emit telemetry (if configured). Runtime MUST still return the suspend response to the requester.

---

## 6. Invariants

`SuspendPolicy` MUST preserve:

- `SuspendEntry` remains the sole terminal entry for the phase.
- `ResumeToken` validity remains unchanged.
- No additional durable mutations occur.
- Execution phase remains suspended.

`SuspendPolicy` MUST NOT influence:

- Execution phase semantics
- Thread concurrency rules
- Timeout behavior
- Resume validation rules

---

## 7. Architectural Guarantees

This design guarantees:

- Canonical thread semantics are preserved.
- Suspend routing is pluggable without altering the execution model.
- Runtime correctness is not dependent on external notification success.
- Multi-user workflows are supported without expanding thread model complexity.

---

## 8. Related Specifications

- FlotillaRuntime
- Thread Model (`SuspendEntry`)
- ResumeToken
- ExecutionConfig