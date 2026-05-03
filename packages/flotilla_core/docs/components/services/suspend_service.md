# SuspendService Specification (v1.2-draft)

## 1. Executive Summary

### Purpose

`SuspendService` defines who should be notified and how when an execution phase terminates with a `SuspendEntry`.

`SuspendService` is strictly post-terminal and non-mutating:

- `SuspendEntry` is authoritative and durable.
- `SuspendService` does not affect thread state.
- `SuspendService` failures are non-fatal.
- `SuspendService` MUST NOT influence execution phase outcome.

`SuspendService` exists to support multi-user environments where the resumer may differ from the requester.

### What SuspendService Does

`SuspendService`:

- Receives a durable `SuspendEntry`
- Receives the issued `ResumeToken`
- Performs synchronous best-effort routing or notification
- MAY emit advisory information (optional, non-authoritative)

### What SuspendService Does Not Do

`SuspendService` MUST NOT:

- Mutate durable state (no `ThreadEntryStore` writes)
- Create or modify `ResumeToken`
- Modify `ThreadContext`
- Determine thread status
- Alter execution outcome
- Influence terminal entry semantics

---

## 2. Architectural Context

Intended execution order:

1. Runtime appends `SuspendEntry` durably.
2. Runtime reloads thread and reconstructs `ThreadContext`.
3. Runtime emits suspend response to the requester.
4. Runtime may invoke `SuspendService` synchronously (best-effort).

`SuspendService` is designed to be invoked after durability and after terminal semantics are established. It cannot alter the canonical shape of the thread.

---

## 3. Core Concepts

`SuspendService` is a post-terminal, best-effort notification service intended to run after a `SuspendEntry` is durably appended.

Core inputs:

- `ThreadContext` reconstructed after durable reload.
- Durable `SuspendEntry` for the terminated phase.
- Issued `ResumeToken` associated with that suspend entry.
- `PhaseContext` used by the phase.

### Canonical Interface

`SuspendService` MUST expose semantics equivalent to:

```python
async def handle_suspend(
    thread_context: ThreadContext,
    suspend_entry: SuspendEntry,
    resume_token: str,
    phase_context: PhaseContext,
) -> None:
    ...
```

### Input Requirements

- `thread_context` MUST reflect durable state after reload.
- `suspend_entry` MUST be the durable terminal entry for the phase.
- `resume_token` MUST correspond to that suspend entry.
- `execution_config` MUST be the `PhaseContext` used for the phase.
- All inputs MUST be treated as immutable.

---

## 4. Responsibilities

`SuspendService` is responsible for:

- Handling suspend information when invoked after durable terminal state is established.
- Performing best-effort routing or notification.
- Returning without mutating durable state.
- Allowing runtime completion to proceed even when notification fails.

## 5. Non-Responsibilities

`SuspendService` is NOT responsible for:

- Creating, modifying, validating, or consuming `ResumeToken`.
- Appending or modifying `ThreadEntry` objects.
- Determining thread status.
- Altering execution outcomes.
- Enforcing resume authorization.

---

## 6. Behavioral Contract

### 4.1 Invocation Timing

When runtime invokes `SuspendService`, it MUST invoke it:

- Only after `SuspendEntry` has been durably appended
- Only after reload of `ThreadContext`
- At most once per runtime request execution

Runtime MUST NOT invoke `SuspendService` before durable mutation.

### 4.2 Synchronous, Non-Blocking Semantics

When invoked, runtime MUST await `SuspendService` completion before exiting runtime execution. However:

- `SuspendService` MUST NOT delay runtime completion indefinitely.
- Runtime SHOULD enforce a configurable timeout for `SuspendService` execution.

### 4.3 Non-Mutating Guarantee

`SuspendService` MUST NOT:

- Write to `ThreadEntryStore`
- Modify any `ThreadEntry`
- Append new entries
- Invalidate `ResumeToken`
- Alter `ThreadContext`

`SuspendService` produces no durable mutations.

---

### Error Handling

`SuspendService` MUST NOT allow errors to leak into runtime execution flow.

- Any exception raised by `SuspendService` MUST be caught by `FlotillaRuntime`.
- Runtime MUST treat `SuspendService` exceptions as non-fatal.

Runtime MUST NOT:

- Append additional `ThreadEntry`
- Convert service failure into `ErrorEntry`
- Alter the terminal state of the execution phase
- Change the emitted suspend response

`SuspendService` failures MUST NOT:

- Cause the execution phase to fail
- Modify thread state
- Invalidate `ResumeToken`
- Affect concurrency semantics

Runtime MAY log the error or emit telemetry (if configured). Runtime MUST still return the suspend response to the requester.

---

## 7. Constraints & Guarantees

`SuspendService` MUST preserve:

- `SuspendEntry` remains the sole terminal entry for the phase.
- `ResumeToken` validity remains unchanged.
- No additional durable mutations occur.
- Execution phase remains suspended.

`SuspendService` MUST NOT influence:

- Execution phase semantics
- Thread concurrency rules
- Timeout behavior
- Resume validation rules

---

### Architectural Guarantees

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
- PhaseContext
