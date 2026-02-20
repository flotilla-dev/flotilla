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

Durable mutation boundaries occur only at:

- `message_final`
- `suspend`
- `error`

**Streaming (`message_chunk`) is ephemeral.**

### ✅ Agents Are Stateless

**Agents do not:**

- Mutate durable thread log
- Persist state
- Incrementally update internal state

Resume safety is achieved by reconstructing execution context entirely from ThreadContext. AgentEvent carries no continuation state.

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
suspend(reason=...,)
```

**InterruptStrategy handles coordination.**

---

## 3️⃣ Canonical AgentEvent Types

The system intentionally uses a very small event set.

### 1️ message_start (Optional, Observability Only)

**Used for:**

- Timing
- Audit tracking
- Performance measurement

**Does NOT mutate durable state.**

```json
{
  "type": "message_start",
  "role": "agent" | "tool",
  "message_id": "string"
}
```

### 2️ message_chunk (Streaming, Text-Only)

**Used for:**

- Streaming partial assistant output
- Streaming partial tool output (text only)

**Must contain text only.**

- Never structured content
- Not eligible checkpoint boundary

```json
{
  "type": "message_chunk",
  "role": "agent" | "tool",
  "message_id": "string",
  "content_text": "partial text"
}
```

### 3️ message_final (Atomic Thread Log Mutation)

**The only message event that produces a durable ThreadEntry (AgentOutput/ToolOutput).**

- Supports full structured multimodal content
- Eligible checkpoint boundary

```json
{
  "type": "message_final",
  "role": "agent" | "tool",
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
- If any message_chunk events are emitted for a message_id, then the concatenation of all chunk text must exactly equal the text represented in message_final for that same message_id.
- message_final must not introduce additional user-visible text that wasn’t streamed in chunks.
- message_final remains the canonical durable representation.
- Binary artifacts should be referenced by URL
- No partial structured streaming
- There is no complete event.  Execution completion is implicit when the event stream ends without suspend or error.

### 4 suspend (Execution Pause)

Represents any pause in execution:

- Human approval
- External callback
- Middleware hold
- Escalation
- Rate limiting

**Not HITL-specific.**

Durable execution pause boundary.

```json
{
  "type": "suspend",
  "reason": "string"
}
```

**Runtime:**

- Persists checkpoint
- Marks execution suspended
- Delegates to InterruptStrategy


### 5 error (Execution Failure)

Represents failure condition.

```json
{
  "type": "error",
  "message": "string",
  "recoverable": true | false,
  "metadata": { ... optional structured data ... }
}
```

Runtime may map error metadata into durable ErrorEntry.details.

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

- If no message_chunk events are emitted for a message_id, message_final represents the complete output.
- Text streaming is supported
- Structured multimodal content is atomic

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


## 7️⃣ What Was Intentionally Removed

To preserve simplicity and scalability, the design explicitly excludes:

- ❌ Tool lifecycle events
- ❌ HITL-specific events
- ❌ Internal state mutation events
- ❌ Graph node events
- ❌ Middleware debug events
- ❌ Binary streaming events

**These remain inside the agent/adapter layer.**



