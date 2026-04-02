# AgentEvent Specification (v3)

## 1. Executive Summary

### Purpose

AgentEvent defines the only canonical contract between:

- `FlotillaAgent` (execution layer)
- `FlotillaRuntime` (orchestration + durability layer)

It models execution lifecycle, not conversation state.

`AgentEvent` represents transient execution signals that may result in durable mutations once processed by the runtime.

It explicitly does **not**:

- Represent persisted thread state
- Encode continuation state
- Represent tool-level events
- Carry internal agent memory
- Model conversation history

### Architectural Role

| Property | Value |
|---|---|
| Layer | Execution-to-runtime boundary |
| Durable | Partially (depends on event type) |
| Persisted | Indirectly (converted to `ThreadEntry` by Runtime) |
| Library-agnostic | Yes |
| Externally pluggable | No |
| Stateless | Yes |
| Deterministic | Yes (given identical Agent output) |

Determinism is defined by:

- Event ordering
- Event type
- Event content

---

## 2. System Architecture Context

### Position in Flotilla

`AgentEvent` sits between:

- `FlotillaAgent.run()` (producer)
- `FlotillaRuntime` (consumer)

It interacts directly with:

- `FlotillaAgent`
- `FlotillaRuntime`
- `ContentPart`

It does **not** directly interact with:

- Durable storage
- Thread persistence logic
- Tool layer

### Interaction Diagram (Conceptual)

```
ThreadContext
    ↓
FlotillaAgent.run()
    ↓
AgentEvent (stream)
    ↓
FlotillaRuntime
    ↓
ThreadEntry (durable boundary)
```

### Boundary Ownership

`AgentEvent` **owns**:
- Execution lifecycle modeling
- Structured output signaling
- Durable mutation intent

`AgentEvent` **must NOT**:
- Persist itself
- Mutate thread state
- Encode continuation state
- Represent internal tool execution

---

## 3. Canonical Types / Interfaces

### Closed Set of Event Types

| Type | Durable? | Description |
|---|---|---|
| `message_start` | No | Observability boundary |
| `message_chunk` | No | Streaming text fragment |
| `message_final` | Yes | Atomic structured output |
| `suspend` | Yes | Durable execution pause |
| `error` | Yes | Durable execution failure |

Only these five types are supported. There is no `complete`, `continuation_state`, tool event type, or debug lifecycle event.

---

## 4. Behavioral Contract

### Execution Phase Lifecycle Rules

For each `parent_entry_id`:

- `message_start` MUST be emitted exactly once.
- `message_start` MUST precede all other events for that phase.
- `message_chunk` events are OPTIONAL.
- EXACTLY ONE terminal event MUST be emitted: `message_final`, `suspend`, or `error`.
- After a terminal event, no additional events may be emitted.
- If `error` is emitted, `message_final` MUST NOT follow.
- If `suspend` is emitted, `message_final` MUST NOT follow.

### Valid Lifecycle Example

```
message_start
message_chunk*
message_final
```

### Empty Output Rule

A phase MUST NOT end without a terminal event. If no user-visible output exists, the agent must emit:

```
message_start
message_final (with empty content)
```

---

## 5. Structural Schema

### Common Fields

| Field | Type | Required | JSON-Serializable |
|---|---|---|---|
| `type` | string (enum) | Yes | Yes |
| `parent_entry_id` | string | Yes | Yes |
| `content` | `List[ContentPart]` | Conditional | Yes |
| `execution_metadata` | object | Optional | Yes |

### `message_start`

```json
{
  "type": "message_start",
  "parent_entry_id": "string"
}
```

- No content
- No durability

### `message_chunk`

```json
{
  "type": "message_chunk",
  "parent_entry_id": "string",
  "content": [
    { "type": "text", "text": "partial text" }
  ]
}
```

Rules:
- MUST contain exactly one `TextPart`
- Not persisted
- Optional

### `message_final`

```json
{
  "type": "message_final",
  "parent_entry_id": "string",
  "content": [ContentPart, ...],
  "execution_metadata": { ... }
}
```

Rules:
- Content MUST be JSON-serializable
- Structured content allowed
- Persisted as `AgentOutput`
- No partial structured streaming allowed

Streaming invariant: if `message_chunk` events were emitted, concatenated chunk text MUST equal the text inside `message_final`, and `message_final` MUST NOT introduce additional user-visible text.

### `suspend`

```json
{
  "type": "suspend",
  "parent_entry_id": "string",
  "content": [ContentPart, ...],
  "execution_metadata": { ... }
}
```

Rules:
- Persisted as `SuspendEntry`
- Execution stops after emission

### `error`

```json
{
  "type": "error",
  "parent_entry_id": "string",
  "content": [ContentPart, ...],
  "execution_metadata": { ... }
}
```

Rules:
- Persisted as `ErrorEntry`
- No `message_final` may follow

### JSON Requirements

- All content MUST be JSON-serializable.
- No hidden continuation state allowed.
- No implicit fields allowed.
- Closed enum enforcement required.

---

## 6. Durable Mutation Boundaries

Only the following events produce durable mutations:

- `message_final`
- `suspend`
- `error`

These are the ONLY durable mutations triggered by `AgentEvent`. `message_start` and `message_chunk` are strictly ephemeral.

---

## 7. Invariants

The following must always hold:

- Exactly one `message_start` per phase.
- Exactly one terminal event per phase.
- No terminal event duplication.
- No events after terminal event.
- `parent_entry_id` must reference initiating entry.
- Event order must be causal.
- `message_chunk` contains exactly one `TextPart`.
- Streaming invariant must hold.
- No continuation state present.
- No implicit event types allowed.

Each invariant must be directly testable.

---

## 8. Extension & Override Points

`AgentEvent` is a **closed protocol**:

- No subclassing permitted.
- No additional event types allowed.
- Adapters and agents MUST conform strictly to this schema.

---

## 9. Error Handling Rules

Contract violations include:

- Missing `message_start`
- Multiple terminal events
- Missing terminal event
- Emitting after terminal
- Invalid content schema
- Illegal event ordering

Runtime MUST treat violations as fatal. Silent fallback is forbidden.

---

## 10. Observability & Telemetry

`execution_metadata` MAY include:

- Token usage
- Timing metrics
- Model information
- Debug traces

Rules:
- Metadata MUST be JSON-serializable.
- Metadata MUST NOT affect deterministic replay.
- Metadata persistence is runtime policy-controlled.

---

## 11. Ordering Guarantees

- Events MUST be yielded in causal order.
- No reordering allowed.
- No artificial delay.
- No buffering beyond engine constraints.
- No hidden mutation of event stream.
- Streaming MUST be pass-through.

---

## 12. Architectural Guarantees

- Stateless event objects
- Deterministic lifecycle modeling
- Strict durable boundary separation
- Library-agnostic protocol
- Closed event type set
- Resume safety via parent linkage
- No continuation state
- Streaming-safe by design

---

## 13. Related Specifications

Only specifications directly interacting with `AgentEvent`:

- FlotillaAgent Specification
- FlotillaRuntime Specification
- ContentPart Specification
- Thread Model Specification