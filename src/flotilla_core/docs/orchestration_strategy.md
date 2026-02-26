# OrchestrationStrategy Specification (v1.1-draft)

## 1. Executive Summary

### Purpose

`OrchestrationStrategy` defines the execution topology of a single execution phase.

It determines:

- How execution proceeds
- Which agents and/or sub-strategies are invoked
- How their outputs are coordinated
- When the phase terminates

It is a pure execution abstraction, intentionally structurally symmetrical to `FlotillaAgent`.

### What OrchestrationStrategy Is

- A phase-scoped execution engine
- A coordinator of one or more `FlotillaAgent` and/or `OrchestrationStrategy` instances
- A producer of canonical `AgentEvent`
- A pluggable execution policy

### What OrchestrationStrategy Is Not

- A durable mutation boundary
- A `ThreadEntryStore` client
- A `ResumeToken` issuer
- A suspend router
- A concurrency manager
- A timeout enforcer
- A side-effect reliability mechanism

All durable mutation and lifecycle enforcement are owned by `FlotillaRuntime`.

---

## 2. Architectural Role

| Property | Value |
|---|---|
| Layer | Runtime Execution Layer |
| Durability | None |
| Statefulness | Must be stateless across invocations |
| Library-agnostic | Yes |

`OrchestrationStrategy` is invoked after:

- A phase-initiating `ThreadEntry` has been durably appended
- `ThreadContext` has been reconstructed

---

## 3. Interface Contract

### Canonical Invocation

`OrchestrationStrategy` MUST expose semantics equivalent to:

```python
async def execute(
    thread_context: ThreadContext,
    execution_config: ExecutionConfig
) -> AsyncIterator[AgentEvent]
```

This signature is intentionally identical in shape to `FlotillaAgent` execution.

---

## 4. Structural Symmetry With FlotillaAgent

`OrchestrationStrategy` and `FlotillaAgent` share the same execution contract:

- **Input:** immutable `ThreadContext` + `ExecutionConfig`
- **Output:** stream of `AgentEvent`
- Exactly one terminal `AgentEvent`
- No out-of-band mutation

Because of this symmetry:

- `OrchestrationStrategy` MAY invoke one or more `FlotillaAgent` instances.
- `OrchestrationStrategy` MAY invoke one or more `OrchestrationStrategy` instances.
- Strategies MAY be nested arbitrarily.
- Execution graphs of arbitrary size and shape are supported.
- The runtime does not distinguish between "agent" and "strategy" at the `AgentEvent` boundary.

---

## 5. Behavioral Contract

### 5.1 Statelessness

`OrchestrationStrategy` MUST:

- Be stateless across invocations.
- Not rely on in-memory persisted state between phases.
- Derive all required execution state from `thread_context`, `execution_config`, and `AgentEvent` produced during execution.

### 5.2 No Durable Mutation

`OrchestrationStrategy` MUST NOT:

- Append `ThreadEntry`
- Modify `ThreadContext`
- Issue `ResumeToken`
- Access `ThreadEntryStore`
- Modify timeout semantics
- Invoke `SuspendPolicy`
- Invoke `TelemetryPolicy` directly

Durable mutation is exclusively owned by `FlotillaRuntime`.

### 5.3 AgentEvent-Only Contract

`OrchestrationStrategy` MUST communicate exclusively via `AgentEvent`. It MUST NOT:

- Raise execution-level exceptions to signal business failure
- Use return values outside the `AgentEvent` stream
- Signal termination via side channels

All execution outcomes MUST be represented as `AgentEvent`.

### 5.4 Error Handling (Strict)

If an unrecoverable error occurs within `OrchestrationStrategy`:

- It MUST yield exactly one `AgentEvent.error`.
- It MUST NOT raise uncaught exceptions.

Raising uncaught exceptions constitutes a contract violation. Runtime MAY defensively convert unexpected exceptions into `AgentEvent.error`, but this is a fallback safety net, not the expected behavior. This rule ensures full symmetry with `FlotillaAgent`.

### 5.5 Terminal Event Requirement

Each invocation MUST yield zero or more non-terminal `AgentEvent` followed by exactly one terminal `AgentEvent`.

Terminal types: `message_final`, `suspend`, `error`

After yielding a terminal `AgentEvent`, no further events may be yielded. Violation MUST be treated as a contract error by the runtime.

### 5.6 Phase Isolation

`OrchestrationStrategy` MUST operate strictly within the execution phase initiated by the most recent `UserInput` or `ResumeEntry`.

It MUST NOT:

- Initiate new phases
- Resume prior phases
- Close phases via durable mutation
- Create nested durable lifecycle boundaries

All orchestration occurs within a single phase.

---

## 6. Composition Rules

`OrchestrationStrategy` MAY:

- Invoke one or more `FlotillaAgent` instances
- Invoke one or more `OrchestrationStrategy` instances
- Perform conditional routing
- Perform hierarchical delegation
- Coordinate parallel or sequential execution
- Aggregate or transform `AgentEvent` streams
- Build arbitrarily complex execution graphs

The framework does not prescribe or restrict execution topology. The only requirement is adherence to the `AgentEvent` contract.

---

## 7. Ordering Guarantees

`OrchestrationStrategy` MUST:

- Preserve causal ordering of `AgentEvent`
- Not reorder events emitted by sub-components
- Not emit events after terminal
- Not suppress terminal events

If internal parallelism is implemented, emitted `AgentEvent` order MUST remain deterministic and causal.

---

## 8. Suspend Semantics

If `OrchestrationStrategy` yields `AgentEvent.suspend`:

- It MUST treat suspend as terminal for the phase.
- It MUST NOT attempt to issue `ResumeToken`.
- It MUST NOT attempt to determine resume routing.
- It MUST yield no further events.

Suspend handling remains runtime-owned.

---

## 9. Crash Semantics

If the runtime process crashes during strategy execution:

- `OrchestrationStrategy` is not responsible for recovery.
- Recovery occurs at the phase level via timeout.
- Strategy MUST be safe to re-run from initial `ThreadContext` state after new phase initiation.
- Strategy MUST NOT assume partial durable progress.

---

## 10. Prohibited Behaviors

`OrchestrationStrategy` MUST NOT:

- Write to durable storage
- Emit non-canonical events
- Raise business exceptions instead of yielding `AgentEvent.error`
- Yield multiple terminal events
- Yield events after terminal
- Depend on runtime implementation details
- Bypass canonical `AgentEvent` contract

---

## 11. Invariants

For every invocation:

- Exactly one terminal `AgentEvent` MUST be yielded.
- All events MUST conform to the canonical `AgentEvent` spec.
- `thread_context` MUST remain immutable.
- `execution_config` MUST remain immutable.
- No durable mutation occurs within strategy.

---

## 12. Architectural Guarantees

This design guarantees:

- Complete symmetry between `FlotillaAgent` and `OrchestrationStrategy`
- Arbitrarily composable execution graphs
- Unified execution abstraction
- No out-of-band error paths
- Strict lifecycle separation
- Strategy neutrality regarding topology
- Runtime remains sole durability authority