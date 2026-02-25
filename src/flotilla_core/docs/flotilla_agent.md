# FlotillaAgent Specification (v3)

## 1. Executive Summary

### Purpose

FlotillaAgent is the stateless execution boundary between:

- `ThreadContext` (durable thread snapshot)
- A reasoning engine (e.g., LangChain)
- The canonical `AgentEvent` protocol

It is:

- Stateless
- Async-only
- Streaming-native
- Library-agnostic at the contract boundary

FlotillaAgent owns the transformation of reasoning-engine output into canonical `AgentEvent` instances.

It explicitly does **not**:

- Mutate durable state
- Append `ThreadEntry`
- Persist checkpoints
- Maintain continuation state
- Store per-thread memory
- Emit non-canonical events

All durable state mutation occurs outside the agent boundary.

### Architectural Role

| Property | Value |
|---|---|
| Layer | Execution / Agent boundary layer |
| Durable | No |
| Persisted | No |
| Library-agnostic | Yes (at `AgentEvent` boundary) |
| Externally pluggable | Yes |
| Stateless | Yes (required) |
| Deterministic | Yes (given same `ThreadContext` + config) |

Deterministic behavior is defined by:

- `ThreadContext` contents
- `ExecutionConfig`
- Injected reasoning engine behavior

---

## 2. System Architecture Context

### Position in Flotilla

FlotillaAgent sits between durable thread state and runtime orchestration.

It interacts directly with:

- `ThreadContext`
- `AgentEvent`
- `FlotillaTool`
- `ContentPart`

It does **not** interact directly with:

- Durable storage
- `ThreadEntry` persistence
- Checkpoint storage

### Interaction Diagram (Conceptual)

```
ThreadContext
    ↓
FlotillaAgent.run()
    ↓
Reasoning Engine
    ↓
Tool Invocation (internal)
    ↓
AgentEvent (canonical)
```

Followed by:

```
AgentEvent → Runtime → ThreadEntry (durable boundary)
```

### Boundary Ownership

FlotillaAgent **owns**:
- `AgentEvent` lifecycle correctness
- Canonical output normalization
- Streaming emission ordering

FlotillaAgent **must NOT**:
- Interpret durable mutation policies
- Persist data
- Control checkpointing
- Access database or storage layers

---

## 3. Canonical Types / Interfaces

### Public API (Single Entry Point)

```python
async def run(
    self,
    thread: ThreadContext,
    config: ExecutionConfig,
) -> AsyncIterator[AgentEvent]
```

Rules:

- Async-only
- Streaming-native
- No separate resume method
- Resume safety achieved via reconstructed `ThreadContext`

### Closed Set: Emitted Event Types

The agent may emit only canonical `AgentEvent` types defined in the AgentEvent specification. No additional event types are allowed. No tool-specific events exist.

---

## 4. Behavioral Contract

### Core Lifecycle Rules

- Agent MUST validate `thread.status == RUNNABLE` before execution.
- Agent MUST emit canonical `AgentEvent` only.
- Agent MUST forward events immediately (no buffering unless engine requires).
- Agent MUST enforce legal event ordering.
- Agent MUST NOT emit durable entries directly.
- Agent MUST NOT mutate `ThreadContext`.
- Agent MUST NOT store continuation state.
- EXACTLY ONE terminal event MUST be emitted per execution phase.
- Agent MUST propagate tool exceptions into an `error` event.
- Agent MUST NOT emit both `error` and `message_final`.

### Empty Output Rule

If the reasoning engine produces no output, the agent MUST emit:

```
message_start
message_final(content=[TextPart("")])
```

Agent MUST NEVER emit zero events.

---

## 5. Structural Schema

### `run()` Parameters

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `thread` | `ThreadContext` | No | Durable snapshot |
| `config` | `ExecutionConfig` | No | Immutable config |

### Emitted Event Requirements

- All emitted events must conform to `AgentEvent` schema.
- All `message_final` events must contain non-null `List[ContentPart]`.
- Events must be JSON-serializable.

### Immutability Constraints

- Agent instances MUST be stateless across calls.
- `ThreadContext` MUST be treated as read-only.
- `ExecutionConfig` MUST NOT be mutated.
- No internal mutable state allowed per execution.

---

## 6. Durable Mutation Boundaries

FlotillaAgent produces **no durable mutations**.

It does **NOT**:
- Append `ThreadEntry`
- Persist checkpoints
- Modify durable thread state

Durable mutations occur only after `AgentEvent` leaves the agent boundary.

---

## 7. Invariants

The following must always hold:

- Stateless execution across calls.
- No per-thread memory retained.
- Exactly one terminal event per execution phase.
- No illegal event ordering.
- No mixed terminal events.
- No mutation of `ThreadContext`.
- Tool invocation is internal only.
- Event emission preserves causal order.
- Resume safety depends solely on `ThreadContext` reconstruction.

Each invariant must be directly testable.

---

## 8. Extension & Override Points

### Template Method Pattern

Base class defines:
```python
async def run(...)
```

Subclass implements:
```python
async def _execute(...)
```

Subclasses **MUST**:
- Emit canonical `AgentEvent` only.
- Preserve ordering invariants.
- Preserve statelessness.
- Normalize outputs to `List[ContentPart]`.

Subclasses **MUST NOT**:
- Emit durable mutations.
- Maintain continuation state.
- Introduce non-canonical event types.

---

## 9. Error Handling Rules

### Execution Failures

If reasoning execution fails:
- Agent MUST emit `error`.
- Agent MUST NOT emit `message_final` afterward.

### Initialization Failures

- MUST raise at construction (fail-fast).
- MUST NOT defer to runtime.

### Tool Exceptions

- MUST propagate to agent.
- MUST result in `error` event (unless subclass explicitly transforms).
- Silent failure is forbidden.

---

## 10. Observability & Telemetry

Agent **MAY**:
- Include metadata within `AgentEvent`.
- Normalize reasoning outputs.
- Attach optional content parts (if allowed by policy).

Agent **MUST NOT**:
- Persist telemetry.
- Modify durable storage.
- Alter determinism based on logging.

Observability MUST NOT affect ordering or determinism.

---

## 11. Ordering Guarantees

- Events MUST be emitted in causal order.
- No artificial reordering.
- No delayed emission.
- Streaming MUST be pass-through.
- No hidden buffering beyond reasoning engine constraints.
- No hidden mutation of event stream.

---

## 12. Architectural Guarantees

- Stateless execution
- Deterministic replay from `ThreadContext`
- Strict durable boundary separation
- Library-agnostic canonical protocol
- No hidden continuation state
- Streaming-native design
- Single execution entry point

---

## 13. Related Specifications

Only specifications directly interacting with FlotillaAgent:

- AgentEvent Specification
- ThreadContext Specification
- ContentPart Specification
- FlotillaTool Specification