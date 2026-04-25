# ExecutionTimeoutPolicy Specification (v3.0)

## 1. Executive Summary

`ExecutionTimeoutPolicy` defines how Flotilla determines whether an execution phase has exceeded its timeout duration.

`ExecutionTimeoutPolicy`:

- Is injectable
- Is stateless
- Is deterministic
- Is side-effect free
- Returns a boolean decision only

It does **not**:

- Enforce timeout
- Append thread entries
- Emit telemetry
- Produce user-facing messages
- Manage timers
- Define configuration mechanisms

It evaluates whether a timeout condition exists.

---

## 2. Architectural Context

`ExecutionTimeoutPolicy` collaborates with:

- `FlotillaRuntime`
- `ThreadContext`

`ExecutionTimeoutPolicy`:

- Receives reconstructed `ThreadContext`
- Receives current wall-clock time
- Returns a boolean decision

`ExecutionTimeoutPolicy` does not access storage directly and does not mutate state.

---

## 3. Core Concepts

`ExecutionTimeoutPolicy` is a stateless policy object that evaluates timeout state from an immutable `ThreadContext` and a caller-supplied `now` timestamp.

Core terms:

- Active execution phase: a phase represented in durable thread state that has not reached a terminal entry.
- Durable timestamp: the store-assigned timestamp on the phase-initiating entry.
- Timeout decision: a boolean result indicating whether runtime should treat the phase as expired.

---

## 4. Responsibilities

`ExecutionTimeoutPolicy` is responsible for:

- Determining whether an active execution phase has exceeded its timeout duration.

---

## 5. Non-Responsibilities

`ExecutionTimeoutPolicy` is NOT responsible for:

- Enforcing timeout
- Appending `ErrorEntry`
- Managing retries
- Emitting telemetry
- Generating error messages
- Managing configuration sources

---

## 6. Behavioral Contract

### Interface Contract

```python
class ExecutionTimeoutPolicy(Protocol):

    def is_expired(
        self,
        thread_context: ThreadContext,
        now: datetime
    ) -> bool:
        ...
```

### Evaluation Semantics

`ExecutionTimeoutPolicy` MUST:

1. Determine whether `thread_context` contains an active execution phase.
2. If no active phase exists, return `False`.
3. If an active phase exists:
   - Identify the initiating entry's store-assigned timestamp.
   - Compute elapsed time using `now`.
   - Compare elapsed duration against the policy's timeout threshold.
   - Return `True` if elapsed time exceeds threshold.
   - Return `False` otherwise.

Durable store timestamps are authoritative. `RuntimeRequest.timestamp` MUST NOT be used.

---

## 7. Constraints & Guarantees

`ExecutionTimeoutPolicy` MUST:

1. Be pure and side-effect free.
2. Not mutate `ThreadContext`.
3. Not depend on in-memory execution state.
4. Use durable timestamps as authoritative.
5. Return identical results for identical inputs.
6. Be safe for concurrent invocation.

`ExecutionTimeoutPolicy` MUST NOT:

- Access `ThreadEntryStore` directly.
- Modify thread state.
- Trigger lifecycle transitions.

---

### Thread Safety

`ExecutionTimeoutPolicy` implementations MUST:

- Be stateless or safely immutable
- Be thread-safe
- Be re-entrant

---

### Non-Fatal Requirement

`ExecutionTimeoutPolicy` MUST NOT cause runtime execution to fail. Any internal failure of the policy MUST NOT be failure-fatal to `FlotillaRuntime`.

---

### Example Implementation

```python
class FixedDurationTimeoutPolicy:

    def __init__(self, timeout_ms: int):
        self._timeout_ms = timeout_ms

    def is_expired(self, thread_context, now):
        if not thread_context.has_active_phase():
            return False

        start_ts = thread_context.active_phase_start_timestamp()
        elapsed_ms = (now - start_ts).total_seconds() * 1000

        return elapsed_ms > self._timeout_ms
```

---

### Architectural Guarantees

This specification guarantees:

- Deterministic timeout evaluation
- Strict separation between evaluation and enforcement
- No lifecycle coupling
- No storage coupling
- No transport coupling
- Minimal implementation surface

## 8. Related Specifications
- Thread Model (`ThreadEntry` / `ThreadContext`)
- FlotilaRuntime
