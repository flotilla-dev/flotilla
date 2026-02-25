# ContentPart Specification (v1.3)

## 1. Executive Summary

### Purpose

`ContentPart` is the canonical structured payload unit used for thread I/O in Flotilla.

It is used symmetrically in:

- `UserInput.content`
- `AgentEvent.message_final.content`
- Durable `AgentOutput.content`

It represents content only — never execution mechanics.

`ContentPart` is:

- JSON-serializable
- Durable-log safe
- Library-agnostic
- Runtime-opaque
- Streaming-compatible (atomic only)
- Deterministic and replayable

It explicitly does **not**:

- Encode execution state
- Encode continuation state
- Represent tool invocation
- Contain raw binary payloads
- Contain runtime references
- Imply mutability or lifecycle semantics

### Architectural Role

| Property | Value |
|---|---|
| Layer | Thread I/O content layer |
| Durable | Yes (when persisted in thread) |
| Persisted | Yes |
| Library-agnostic | Yes |
| Externally pluggable | Closed union with controlled extension |
| Stateless | Yes |
| Deterministic | Yes |

Determinism is defined by:

- JSON-serializable structure
- Immutable representation once written

---

## 2. System Architecture Context

### Position in Flotilla

`ContentPart` sits inside:

- `AgentEvent` (`message_final`, `suspend`, `error`)
- `ThreadEntry` durable records
- `UserInput`

It interacts directly with:

- `AgentEvent`
- Thread Model
- `FlotillaAgent`

It does **not** interact with:

- Runtime orchestration logic
- Tool execution
- Checkpointing

### Interaction Diagram (Conceptual)

```
UserInput.content → ThreadEntry (durable)
                         ↓
                  FlotillaAgent
                         ↓
                AgentEvent.message_final
                         ↓
                  ThreadEntry (durable)
```

### Boundary Ownership

`ContentPart` **owns**:
- Structured content modeling
- Typed payload semantics
- Deterministic durable representation

It **must NOT**:
- Contain execution mechanics
- Influence runtime behavior
- Encode graph or workflow state

---

## 3. Canonical Types / Interfaces

### Discriminated Union (Closed Set)

Every `ContentPart` MUST contain a `"type"` field that determines the allowed fields:

```json
{
  "type": "<discriminator>"
}
```

No implicit modality, no open metadata blobs, no dynamic field injection.

### Supported Types (Closed Set)

| Type | Durable? | Description |
|---|---|---|
| `text` | Yes | Plain text |
| `json` | Yes | Structured JSON object |
| `file` | Yes | External file reference |
| `reasoning` | Yes | LLM reasoning description |
| `confidence` | Yes | LLM confidence score |

Only these five types are supported.

---

## 4. Behavioral Contract

### Core Rules

- `ContentPart` MUST include `"type"`.
- Fields MUST conform exactly to the type schema.
- Structured content MUST be emitted only in `message_final`.
- Structured content MUST NOT be partially streamed.
- Runtime MUST treat `ContentPart` as opaque.
- `ContentPart` MUST be JSON-serializable.
- IDs (if present) MUST be unique within a single message.
- `ContentPart` MUST NOT contain raw binary.
- `ContentPart` MUST NOT contain execution state.
- `ContentPart` MUST be immutable once persisted.

### Atomic Emission Rule

Structured parts (`json`, `file`, `reasoning`, `confidence`) MUST:

- Appear only in `message_final`
- Be complete and self-contained
- Not be streamed incrementally

---

## 5. Structural Schema

### Common Optional Field

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | Optional | Unique within message |

If `id` is present, it MUST be unique within a single `message_final` and has no cross-message or lifecycle semantics.

### 5.1 TextPart

```json
{
  "type": "text",
  "text": "Hello world",
  "id": "optional"
}
```

Required fields: `type = "text"`, `text` (string)

Rules:
- May be empty string
- Streaming reconstruction must match final value exactly
- No MIME type
- No binary

### 5.2 JsonPart

```json
{
  "type": "json",
  "data": { "key": "value" },
  "id": "optional"
}
```

Required fields: `type = "json"`, `data` (JSON-serializable object)

Rules:
- Must be JSON-serializable
- No custom objects
- No execution metadata

### 5.3 FilePart

```json
{
  "type": "file",
  "url": "https://example.com/file.pdf",
  "mime_type": "application/pdf",
  "bytes": 1048576,
  "sha256": "abc123...",
  "id": "optional"
}
```

Required fields: `type = "file"`, `url` (string), `mime_type` (string)

Optional fields: `bytes` (integer), `sha256` (string)

Rules:
- URL must reference external content
- No raw binary allowed
- If `sha256` is present, MUST be a 64-character hex string
- Runtime does not interpret MIME type

### 5.4 ReasoningPart

```json
{
  "type": "reasoning",
  "reason": "...",
  "id": "optional"
}
```

Required fields: `type = "reasoning"`, `reason` (string)

Rules:
- Textual explanation of LLM reasoning
- Policy-controlled exposure
- No execution metadata

### 5.5 ConfidencePart

```json
{
  "type": "confidence",
  "score": 0.37,
  "id": "optional"
}
```

Required fields: `type = "confidence"`, `score` (float)

Rules:
- Score range MUST be between `0.0` and `1.0` inclusive
- Represents model confidence
- No execution state

---

## 6. Durable Mutation Boundaries

`ContentPart` itself does not mutate durable state. Durability occurs when `ContentPart` is stored inside:

- `UserInput`
- `AgentOutput`
- `SuspendEntry`
- `ErrorEntry`

These are the ONLY durable contexts for `ContentPart`.

---

## 7. Invariants

The following must always hold:

- `"type"` discriminator must be present.
- Only defined types are allowed.
- No extra undefined fields permitted.
- IDs (if present) unique within message.
- No raw binary payloads.
- All values JSON-serializable.
- Streaming invariant must hold for text.
- Structured content not streamed.
- Immutable once written.
- Deterministic representation for replay.

Each invariant must be testable.

---

## 8. Extension & Override Points

`ContentPart` union is closed but extensible via spec revision. To introduce a new type:

- Define new `"type"` discriminator
- Define full schema
- Ensure JSON-serializability
- Ensure runtime opacity
- Ensure durability safety

No dynamic runtime registration allowed. Spec revision required for extension.

---

## 9. Error Handling Rules

Contract violations include:

- Missing `"type"`
- Unknown type discriminator
- Non-JSON-serializable values
- Duplicate `id` within message
- Streaming structured content
- Raw binary embedded

Violations MUST fail-fast during validation. Silent coercion is forbidden.

---

## 10. Observability & Telemetry

`ContentPart` MAY contain `reasoning` and `confidence` parts. These are content-level constructs, not runtime telemetry.

Execution telemetry belongs in `AgentEvent.execution_metadata`, not `ContentPart`. Runtime must not interpret `ContentPart` fields.

---

## 11. Ordering Guarantees

- Order of parts within `message_final` MUST be preserved.
- Clients MUST render in order.
- No implicit reordering.
- No structural guessing by runtime.

---

## 12. Architectural Guarantees

- Deterministic durable representation
- Strict separation of execution and content
- Runtime opacity
- Streaming-safe structured output
- Closed discriminated union
- Client-selectable content via `id`
- Replay-safe
- No lifecycle semantics embedded

---

## 13. Related Specifications

Only specifications directly interacting with `ContentPart`:

- AgentEvent Specification
- Thread Model Specification
- FlotillaAgent Specification