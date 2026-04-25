# AgentEvent Specification (v3)

## 1. Executive Summary

`AgentEvent` defines the only canonical contract between `FlotillaAgent` and `FlotillaRuntime`.

It models transient execution lifecycle signals, not persisted conversation state. Runtime may convert terminal `AgentEvent` objects into durable `ThreadEntry` objects, but events do not persist themselves.

`AgentEvent` exists to:

- Represent agent execution progress and terminal outcomes.
- Carry agent-produced `ContentPart` output.
- Provide a closed, library-agnostic event protocol.
- Separate agent execution from runtime durability.

## 2. Architectural Context

`AgentEvent` sits at the execution-to-runtime boundary.

Direct producer:

- `FlotillaAgent.run()`

Consumer:

- `FlotillaRuntime`

`OrchestrationStrategy` is an internal runtime collaborator that may contribute `AgentEvent` streams to `FlotillaRuntime`, but it is not a direct calling-code API.

Related data types:

- `ThreadContext` provides the durable execution history used by the producer.
- `ContentPart` carries user-visible or machine-readable event content.
- `ThreadEntry` is the durable representation produced by runtime from terminal events.

Conceptual flow:

```text
ThreadContext
    -> FlotillaAgent.run()
    -> AgentEvent stream
    -> FlotillaRuntime
    -> ThreadEntry durable boundary
```

`AgentEvent` does not directly interact with durable storage, thread persistence logic, transport adapters, or the tool layer.

## 3. Core Concepts

### Closed Event Types

| Type | Durable? | Description |
|---|---|---|
| `message_start` | No | Observability boundary |
| `message_chunk` | No | Streaming text fragment |
| `message_final` | Yes | Atomic structured output |
| `suspend` | Yes | Durable execution pause |
| `error` | Yes | Durable execution failure |

Only these five event types are supported. There is no `complete`, `continuation_state`, tool event type, or debug lifecycle event.

### Common Fields

| Field | Type | Required | JSON-Serializable |
|---|---|---|---|
| `type` | string enum | Yes | Yes |
| `previous_entry_id` | string | Yes | Yes |
| `agent_id` | string | Yes | Yes |
| `content` | `List[ContentPart]` | No; defaults to empty list | Yes |
| `execution_metadata` | object | Optional | Yes |
| `is_terminal` | boolean | Yes | Yes |

### Event Schemas

`message_start`:

```json
{
  "type": "message_start",
  "previous_entry_id": "string",
  "agent_id": "string",
  "content": [],
  "is_terminal": false
}
```

`message_start` has empty content and produces no durable mutation.

`message_chunk`:

```json
{
  "type": "message_chunk",
  "previous_entry_id": "string",
  "agent_id": "string",
  "content": [
    { "type": "text", "text": "partial text" }
  ],
  "is_terminal": false
}
```

`message_chunk` MUST contain exactly one `TextPart`. It is optional and is not persisted.

`message_final`:

```json
{
  "type": "message_final",
  "previous_entry_id": "string",
  "agent_id": "string",
  "content": [ContentPart, "..."],
  "execution_metadata": {},
  "is_terminal": true
}
```

`message_final` is persisted by runtime as `AgentOutput`.

`suspend`:

```json
{
  "type": "suspend",
  "previous_entry_id": "string",
  "agent_id": "string",
  "content": [ContentPart, "..."],
  "execution_metadata": {},
  "is_terminal": true
}
```

`suspend` is persisted by runtime as `SuspendEntry`. Execution stops after emission.

`error`:

```json
{
  "type": "error",
  "previous_entry_id": "string",
  "agent_id": "string",
  "content": [ContentPart, "..."],
  "execution_metadata": {},
  "is_terminal": true
}
```

`error` is persisted by runtime as `ErrorEntry`. No `message_final` may follow.

## 4. Responsibilities

`AgentEvent` is responsible for:

- Representing agent execution progress and terminal outcomes.
- Providing the only communication channel from agents and orchestration strategies to runtime.
- Carrying `ContentPart` output without causing durable mutation directly.
- Identifying terminal events that runtime can map into durable thread entries.
- Maintaining a closed event type set.

## 5. Non-Responsibilities

`AgentEvent` is NOT responsible for:

- Appending `ThreadEntry` objects.
- Persisting itself.
- Enforcing runtime lifecycle transitions.
- Issuing or validating `ResumeToken` values.
- Performing orchestration, timeout handling, or suspend routing.
- Representing internal tool execution.
- Encoding continuation state or internal agent memory.
- Defining transport-level runtime I/O.

## 6. Behavioral Contract

### Execution Phase Lifecycle

For each `previous_entry_id`:

- `message_start` MUST be emitted exactly once.
- `message_start` MUST precede all other events for that phase.
- `message_chunk` events are OPTIONAL.
- Exactly one terminal event MUST be emitted: `message_final`, `suspend`, or `error`.
- After a terminal event, no additional events may be emitted.
- If `error` is emitted, `message_final` MUST NOT follow.
- If `suspend` is emitted, `message_final` MUST NOT follow.

Valid lifecycle:

```text
message_start
message_chunk*
message_final
```

### Empty Output

A phase MUST NOT end without a terminal event. If no user-visible output exists, the agent MUST emit:

```text
message_start
message_final (with at least one `ContentPart`)
```

### Content Rules

- All content MUST be JSON-serializable.
- `message_chunk` MUST contain exactly one `TextPart`.
- Every materialized event has a `content` field; if omitted on construction it defaults to an empty list.
- `message_start` content MUST be an empty list.
- `message_final` MUST carry at least one `ContentPart`.
- `suspend` and `error` MAY carry empty content unless stricter runtime or application policy applies.
- Structured content is allowed on terminal events.
- Partial structured streaming is not allowed.
- If `message_chunk` events were emitted, concatenated chunk text MUST equal the text inside `message_final`.
- If `message_chunk` events were emitted, `message_final` MUST NOT introduce additional user-visible text.

### Error Handling

Contract violations include:

- Missing `message_start`.
- Multiple terminal events.
- Missing terminal event.
- Emitting after terminal.
- Invalid content schema.
- Illegal event ordering.
- Unknown event type.
- Hidden continuation state.
- Implicit or undeclared fields.

Runtime MUST treat contract violations as fatal. Silent fallback is forbidden.

## 7. State Model

`AgentEvent` objects are stateless execution signals.

Only the following event types may result in durable mutations:

- `message_final`
- `suspend`
- `error`

These events do not mutate durable state directly. `FlotillaRuntime` owns conversion from terminal `AgentEvent` to durable `ThreadEntry`.

`message_start` and `message_chunk` are strictly ephemeral.

## 8. Interaction Model

`AgentEvent` is produced as an ordered stream by an agent or orchestration strategy and consumed by runtime.

Interaction rules:

- Events MUST be yielded in causal order.
- No reordering is allowed.
- No events may be yielded after a terminal event.
- Streaming MUST be pass-through except for engine constraints.
- Runtime consumes non-terminal events for streaming and observability.
- Runtime consumes terminal events for durable mutation and runtime output.

## 9. Extension Points

`AgentEvent` is a closed protocol.

- No subclassing is permitted.
- No additional event types are allowed.
- No implicit fields are allowed.
- Adapters and agents MUST conform strictly to this schema.

`execution_metadata` is the only sanctioned extension surface. It MAY carry JSON-serializable diagnostic metadata such as token usage, timing metrics, model information, or debug traces.

## 10. Constraints & Guarantees

`AgentEvent` guarantees:

- Stateless event objects.
- Deterministic lifecycle modeling based on event ordering, type, and content.
- Strict durable boundary separation.
- Library-agnostic protocol.
- Closed event type set.
- Resume safety through `previous_entry_id` linkage.
- No continuation state.
- Streaming-safe event flow.

The following invariants MUST always hold:

- Exactly one `message_start` per phase.
- Exactly one terminal event per phase.
- No terminal event duplication.
- No events after a terminal event.
- `previous_entry_id` MUST reference the initiating entry.
- Event order MUST be causal.
- `message_chunk` MUST contain exactly one `TextPart`.
- Streaming content parity MUST hold between chunks and final content.
- No continuation state may be present.
- No implicit event types are allowed.

Each invariant must be directly testable.

## 11. Observability

`message_start` provides an observability boundary for the beginning of agent output.

`execution_metadata` MAY include:

- Token usage.
- Timing metrics.
- Model information.
- Debug traces.

Metadata rules:

- Metadata MUST be JSON-serializable.
- Metadata MUST NOT affect deterministic replay.
- Metadata persistence is runtime policy-controlled.

## 12. Related Specifications

- FlotillaAgent Specification
- OrchestrationStrategy Specification
- FlotillaRuntime Specification
- Runtime I/O Specification
- ContentPart Specification
- Thread Model Specification
