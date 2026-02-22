# Flotilla ContentPart Specification (v1.2)

## 1️⃣ Purpose

ContentPart is the canonical structured output unit emitted inside:

```python
AgentEvent(type="message_final", content=[ContentPart, ...])
```

It represents atomic, user-visible output from an agent.

It is:

- JSON-serializable
- Durable-log safe
- Library-agnostic
- Runtime-opaque
- Streaming-compatible (atomic only)

**ContentPart is the core return type from the agent to the user.**

---

## 2️⃣ Design Principles

### ✅ Discriminated Union

Every ContentPart must include:

```json
{
  "type": "<discriminator>"
}
```

The `"type"` field determines the allowed fields.

- No implicit modality
- No runtime interpretation

### ✅ Atomic Emission Only

Structured content:

- MUST only be emitted in `message_final`
- MUST NOT be partially streamed
- MUST be complete and self-contained

### ✅ Explicit Optional Attributes Per Type

Optional attributes must be:

- Explicitly defined
- Strictly typed
- Valid only for that ContentPart type

**No open-ended metadata objects are allowed.**

### ✅ Runtime-Opaque

The runtime:

- Stores ContentPart as-is
- Does not inspect or modify fields
- Does not interpret MIME types
- Does not render content

**Consumers determine rendering behavior.**

---

## 3️⃣ Canonical ContentPart Types

### 3.1 TextPart

Represents plain text output.

```json
{
  "type": "text",
  "text": "Hello world",
  "id": "part_1"
}
```

#### Required Fields

- `type = "text"`
- `text: string`

#### Optional Fields

- `id: string`

#### Rules

- May be empty string
- Streaming text must reconstruct exactly into this value
- No MIME type
- No binary

---

### 3.2 JsonPart

Represents structured JSON data.

```json
{
  "type": "json",
  "data": { "key": "value" },
  "id": "ui_data"
}
```

#### Required Fields

- `type = "json"`
- `data: JSON-serializable object`

#### Optional Fields

- `id: string`

#### Rules

- Must be JSON-serializable
- No custom objects
- No binary
- No execution metadata

---

### 3.3 FilePart

Represents any file or binary artifact.

```json
{
  "type": "file",
  "url": "https://example.com/file.pdf",
  "mime_type": "application/pdf",
  "bytes": 1048576,
  "sha256": "abc123...",
  "id": "attachment_1"
}
```

#### Required Fields

- `type = "file"`
- `url: string`
- `mime_type: string`

#### Optional Fields

- `id: string`
- `bytes: integer`
- `sha256: string`

#### Field Definitions

**url**

- Must reference externally accessible content
- Must not contain raw binary payload

**mime_type**

- Must accurately describe file format
- Used by client to determine rendering behavior
- Runtime does not interpret it

**bytes**

- Optional size hint
- Must reflect actual file size if provided

**sha256**

- Optional integrity hash
- Must represent SHA-256 of file contents if provided
- Runtime does not validate it

---

## 4️⃣ ContentPart id Semantics (Normative)

The `id` field is:

- Optional but strongly recommended when emitting multiple structured parts
- A semantic handle for selecting a specific part within a single `message_final`
- Opaque to the runtime

### Uniqueness Rules

- If present, `id` MUST be unique within a single `message_final`
- No global uniqueness requirement
- No cross-message identity implied

### Intended Usage

`id` enables clients to:

- Select specific structured parts (e.g., "ui_data" vs "ui_schema")
- Render specific components deterministically
- Perform client-side mapping
- Avoid positional inference
- Avoid structural guessing

#### Example

```json
[
  { "type": "json", "id": "ui_data", "data": {...} },
  { "type": "json", "id": "ui_schema", "data": {...} },
  { "type": "text", "text": "Rendering instructions attached." }
]
```

The consumer may directly select "ui_data" and "ui_schema".

### Explicit Non-Semantics of id

The `id` field:

- Does NOT imply durability semantics
- Does NOT imply cross-message identity
- Does NOT imply mutability
- Does NOT imply patch/update semantics
- Does NOT imply incremental rendering
- Does NOT imply lifecycle state

**It is strictly a content-level selector.**

---

## 5️⃣ Streaming Compatibility Rules

### When Streaming Text

- All `message_chunk.content_text` must concatenate exactly to the `TextPart.text`
- No additional user-visible text may appear in `message_final`

### Structured Content

- Must not be streamed
- Must appear only in `message_final`

**File parts are never streamed.**

---

## 6️⃣ Multiple ContentParts in a Message

A single `message_final` may contain multiple parts:

```json
[
  { "type": "text", "text": "Here is your report." },
  { "type": "file", "url": "...", "mime_type": "application/pdf", "id": "report_pdf" }
]
```

### Rules

- Order is preserved
- Clients render in order
- Each part is independent
- IDs (if present) must be unique within the message

---

## 7️⃣ What ContentPart Must NOT Contain

ContentPart must never contain:

- ❌ Raw binary payloads
- ❌ Runtime-specific references
- ❌ Execution state
- ❌ Continuation state
- ❌ Tool call arguments
- ❌ Graph structure
- ❌ Non-JSON-serializable types
- ❌ Open-ended metadata blobs

---

## 8️⃣ Durable Log Alignment

ContentPart is stored inside:

- `AgentOutput.content`
- `ToolOutput.content`

Therefore it must be:

- Deterministic
- Replayable
- Immutable once written
- Fully serializable

---

## 9️⃣ Extensibility Model

Future types may be introduced by defining new `"type"` discriminators.

### Requirements

- JSON-serializable
- Runtime-opaque
- No execution leakage
- Durable-safe

### Example

```json
{
  "type": "audio",
  "url": "...",
  "mime_type": "audio/mpeg",
  "bytes": 12345
}
```

**No runtime changes required.**

---

## 🔟 Architectural Guarantees

This design guarantees:

- ✅ Strict execution/content separation
- ✅ Deterministic durable representation
- ✅ Streaming-safe structured output
- ✅ Client-level selection via `id`
- ✅ No runtime modality logic
- ✅ File integrity support
- ✅ Infinite extensibility without schema chaos

---

## Final Mental Model

ContentPart is:

- The atomic, user-visible output unit
- The durable representation of agent/tool results
- A strongly typed, structured payload
- Selectable via `id` within a message
- Completely separate from execution state

**It contains content only — never execution mechanics.**