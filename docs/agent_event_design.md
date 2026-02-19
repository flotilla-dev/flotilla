# Flotilla AgentEvent Design Summary

## 1️⃣ Design Philosophy

AgentEvent defines the only contract between:

- **FlotillaAgent** (reasoning layer)
- **FlotillaRuntime** (orchestration + durability layer)

### It Must Be

- Minimal
- Semantic
- Library-agnostic
- Serializable
- Streaming-safe
- Resume-safe
- Future-proof

### AgentEvent Is NOT

- A reflection of LangChain callbacks
- A graph debugging hook
- A tool lifecycle trace
- A middleware notification system
- A UI rendering event

**It represents meaningful orchestration state transitions.**

---

## 2️⃣ Core Principles

### ✅ Runtime Reacts — It Does Not Interpret

**Runtime:**

- Switches on event type
- Applies deterministic state changes
- Delegates checkpointing
- Delegates interrupt handling
- Streams outward

**Runtime does not:**

- Inspect library internals
- Understand tools
- Understand modality
- Understand graph structure

### ✅ Atomic Durable Boundaries

Checkpoint-safe boundaries occur only at:

- `message_final`
- `suspend`
- `complete`
- `error`

**Streaming (`message_chunk`) is ephemeral.**

### ✅ Agents Are Stateless

**Agents do not:**

- Mutate conversation state
- Persist state
- Incrementally update internal state

**Continuation state is emitted atomically only on `suspend` or `complete`.**

### ✅ No Tool-Specific Events

Tool execution is represented as messages:

- Tool output = `message_final(role="tool")`

**No:**

- `tool_call_started`
- `tool_call_completed`
- `tool_output_chunk`

**Tool lifecycle remains inside agent/adapter.**

### ✅ No HITL-Specific Events

Human-in-the-loop is not a special event.

It is simply:

```python
suspend(reason=..., continuation_state=...)
```

**InterruptStrategy handles coordination.**

---

## 3️⃣ Canonical AgentEvent Types

The system intentionally uses a very small event set.

### 1️⃣ message_start (Optional, Observability Only)

**Used for:**

- Timing
- Audit tracking
- Performance measurement

**Does NOT mutate durable state.**

```json
{
  "type": "message_start",
  "role": "assistant" | "tool",
  "message_id": "string"
}
```

### 2️⃣ message_chunk (Streaming, Text-Only)

**Used for:**

- Streaming partial assistant output
- Streaming partial tool output (text only)

**Must contain text only.**

- Never structured content
- Not eligible checkpoint boundary

```json
{
  "type": "message_chunk",
  "role": "assistant" | "tool",
  "message_id": "string",
  "content": "partial text"
}
```

### 3️⃣ message_final (Atomic Conversation Mutation)

**The only event that appends to ConversationState.**

- Supports full structured multimodal content
- Eligible checkpoint boundary

```json
{
  "type": "message_final",
  "role": "assistant" | "tool",
  "message_id": "string",
  "content": [ContentPart, ...],
  "metadata": { ... optional ... }
}
```

#### ContentPart (Structured)

Structured list supports multimodal output.

**Examples:**

```json
{ "type": "text", "text": "Here is your image:" }
{ "type": "image", "url": "...", "mime_type": "image/png" }
{ "type": "json", "data": { ... } }
```

**Rules:**

- `message_chunk` = text only
- Structured content only allowed in `message_final`
- Binary artifacts should be referenced by URL
- No partial structured streaming

### 4️⃣ suspend (Execution Pause)

Represents any pause in execution:

- Human approval
- External callback
- Middleware hold
- Escalation
- Rate limiting

**Not HITL-specific.**

Atomic continuation boundary.

```json
{
  "type": "suspend",
  "reason": "string",
  "continuation_state": { ... deterministic state ... }
}
```

**Runtime:**

- Persists checkpoint
- Marks execution suspended
- Delegates to InterruptStrategy

### 5️⃣ complete (Execution Finished)

Marks successful completion.

Optional continuation state allowed.

```json
{
  "type": "complete",
  "continuation_state": { ... optional ... }
}
```

**Runtime:**

- Persists final checkpoint
- Marks thread complete

### 6️⃣ error (Execution Failure)

Represents failure condition.

```json
{
  "type": "error",
  "message": "string",
  "recoverable": true | false
}
```

**Runtime decides:**

- Suspend?
- Retry?
- Fail terminally?

---

## 4️⃣ Streaming Model

### Event Flow

```
Library Engine
    → AdapterEvent
    → AgentEvent
    → Runtime
    → Client
```

- **Text streaming is supported**
- **Structured multimodal content is atomic**

**Checkpointing occurs only at semantic boundaries.**

---

## 5️⃣ Multimodal Support

Images, JSON, audio, and future content types are supported via:

```python
message_final(content=[ContentPart...])
```

- No new event types required
- No modality-specific runtime logic required

**Runtime treats content as opaque structured data.**

---

## 6️⃣ Checkpoint Alignment

Checkpoint remains:

- Fully serializable
- Deterministic
- Independent of library internals
- Atomic at suspend/complete boundaries

**No incremental `internal_state_update` events.**

**Continuation state is emitted atomically.**

---

## 7️⃣ What Was Intentionally Removed

To preserve simplicity and scalability, the design explicitly excludes:

- ❌ Tool lifecycle events
- ❌ HITL-specific events
- ❌ Internal state mutation events
- ❌ Graph node events
- ❌ Middleware debug events
- ❌ Binary streaming events

**These remain inside the agent/adapter layer.**

---

## 8️⃣ Architectural Guarantees

The AgentEvent contract guarantees:

- ✅ Library neutrality
- ✅ Minimal runtime complexity
- ✅ Deterministic resume
- ✅ Atomic artifact handling
- ✅ Streaming safety
- ✅ Multimodal extensibility
- ✅ Future-proof event stability

---

## Final Assessment

The AgentEvent design is:

- ✅ Tight
- ✅ Minimal
- ✅ Scalable
- ✅ Durable-aware
- ✅ Streaming-native
- ✅ Modality-agnostic
- ✅ Production-ready in philosophy

**It provides a stable and extensible contract between reasoning engines and orchestration runtime.**