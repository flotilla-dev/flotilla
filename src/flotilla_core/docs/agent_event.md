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

## 3️⃣ Message Lifecycle Contract (Mandatory)

For each `message_id`:

1. `message_start` MUST be emitted exactly once
2. It MUST precede any `message_chunk` or `message_final`
3. `message_final` MUST be emitted exactly once
4. `message_chunk` events are optional

### Valid Lifecycle

```
message_start
message_chunk*
message_final
```

### If `error` Is Emitted for a message_id

- No `message_final` may follow

---

## 4️⃣ message_start

Observability boundary event.

```json
{
  "type": "message_start",
  "message_id": "string"
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
  "message_id": "string",
  "content_text": "partial text"
}
```

### Rules

- Text only
- Never structured content
- Not persisted
- Optional

---

## 6️⃣ message_final (Durable Mutation Boundary)

Atomic structured output.

```json
{
  "type": "message_final",
  "message_id": "string",
  "content": [ContentPart, ...],
  "metadata": { ... optional ... }
}
```

### Rules

- Structured content allowed
- Must be JSON-serializable
- Persisted as `AgentOutput`
- No partial structured streaming

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
  "reason": "string"
}
```

- Persisted as `SuspendEntry`
- Execution stops after suspend

---

## 8️⃣ error

Execution failure.

```json
{
  "type": "error",
  "message": "string",
  "recoverable": true,
  "metadata": { ... optional ... }
}
```

### Rules

- `recoverable` defaults to `true`
- Metadata must be JSON-serializable
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