# Flotilla AgentEvent Specification (v3)

## 1️⃣ Purpose

`AgentEvent` defines the only contract between:

- `FlotillaAgent` (execution layer)
- `FlotillaRuntime` (orchestration + durability layer)

**It models execution lifecycle — not conversation state.**

### AgentEvent Is

- Stateless
- Library-agnostic
- Streaming-safe
- Serializable
- Resume-safe
- Not persisted directly

---

## 2️⃣ Canonical Event Types

FlotillaAgent may emit only:

| Type           | Durable? |
|----------------|----------|
| message_start  | ❌ No    |
| message_chunk  | ❌ No    |
| message_final  | ✅ Yes   |
| suspend        | ✅ Yes   |
| error          | ✅ Yes   |

### There Is No

- `complete`
- `continuation_state`
- Tool events
- Lifecycle debug events

**Execution completion is implicit when the stream ends without `suspend` or `error`.**

---

## 3️⃣ Execution Phase Lifecycle Contract (Mandatory)

For each `entry_id`:

1. `message_start` Required exactly once per execution phase (parent_entry_id)
2. It MUST precede any `message_chunk` or `message_final`
3. `message_chunk` events are optional
4. For a given parent_entry_id, exactly one of:
  - message_final
  - suspend
  - error
  must be emitted.

### Valid Lifecycle

```
message_start
message_chunk*
message_final
```

### If `error` Is Emitted for an entry_id

- No `message_final` may follow

---

## 4️⃣ message_start

Observability boundary event.

```json
{
  "type": "message_start",
  "parent_entry_id": "string"
}
```

- Required exactly once per message
- Does not mutate durable state

---

## 5️⃣ message_chunk (Streaming)

Text-only streaming event.

```json
{
  "type": "message_chunk",
  "parent_entry_id": "string",
  "content": [
    { "type": "text", "text": "partial text" }
  ]
}
```

### Rules

- Content MUST contain exactly one TextPart
- Not persisted
- Optional

---

## 6️⃣ message_final (Durable Mutation Boundary)

Atomic structured output.

```json
{
  "type": "message_final",
  "parent_entry_id": "string",
  "content": [ContentPart, ...],
  "execution_metadata": { ... optional ... }
}
```

### Rules

- Structured content allowed
- Must be JSON-serializable
- Persisted as `AgentOutput`
- No partial structured streaming
- Execution metadata is optional execution telemetry (token usage, timing, stack trace)

### Streaming Invariant

If `message_chunk` events were emitted:

- The concatenation of all chunk text MUST equal the text inside `message_final`
- `message_final` must not introduce additional user-visible text

---

## 7️⃣ suspend

Durable execution pause.

```json
{
  "type": "suspend",
  "parent_entry_id": "...",
  "content": [ContentPart, ...],
  "execution_metadata": { ... optional ... }
}
```

- Persisted as `SuspendEntry`
- Execution stops after suspend
- Execution metadata is optional execution telemetry (token usage, timing, stack trace)

---

## 8️⃣ error

Execution failure.

```json
{
  "type": "error",
  "parent_entry_id": "...",
  "content": [ContentPart, ...],
  "execution_metadata": { ... optional ... }
}
```

### Rules

- Execution metadata is optional execution telemetry (token usage, timing, stack trace)
- No `message_final` after error
- Persisted as `ErrorEntry`

---

## 9️⃣ Durable Mutation Boundaries

Only these events produce durable thread entries:

- `message_final`
- `suspend`
- `error`

**`message_chunk` and `message_start` are ephemeral.**

---

## 🔟 Ordering Guarantees

Events must be yielded:

- In causal order
- Without reordering
- Without buffering
- Without artificial delay

---

## 1️⃣1️⃣ Related Specifications

- ContentPart Specification
- Thread Model Specification
- FlotillaAgent Specification