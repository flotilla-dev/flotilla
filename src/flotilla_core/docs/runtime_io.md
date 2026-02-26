# Runtime I/O Specification (v1.3-final)

## 1. Executive Summary

This specification defines the external I/O contract for `FlotillaRuntime`.

It specifies:

- `RuntimeRequest` — input to runtime
- `RuntimeResponse` — synchronous terminal result
- `RuntimeEvent` — streaming execution model
- `ResumeToken` — opaque resume mechanism

These types are transport-agnostic, JSON-serializable, execution-phase scoped, and independent of HTTP specifics. They encode runtime execution semantics only.

They do **not** encode:

- Business logic
- Storage semantics
- Concurrency rules
- Lifecycle enforcement

Execution lifecycle rules, durable append semantics, CAS enforcement, and terminal state guarantees are defined exclusively in the FlotillaRuntime specification.

---

## 2. RuntimeRequest

### Purpose

Represents a single execution phase attempt. Each valid `RuntimeRequest` results in exactly one execution phase initiation attempt.

### Structural Schema

```json
{
  "runtime_key": "string",
  "thread_id": "string",
  "user_id": "string",
  "request_id": "string",
  "timestamp": "ISO-8601 string",
  "correlation_id": "string | null",
  "trace_id": "string | null",
  "resume_token": "string | null",
  "input": [ "ContentPart" ],
  "transport_metadata": { "...": "..." }
}
```

### Field Definitions

**`runtime_key`** (REQUIRED) — Identifies which runtime implementation to use. MUST match a registered runtime. MUST be supplied at application boundary.

**`thread_id`** (REQUIRED) — Identifies the thread to execute against. MUST refer to an existing thread. Runtime MUST fail if thread does not exist. Runtime MUST NOT create thread.

**`user_id`** (REQUIRED) — Identifies the requesting user. Used for auditing and may influence policy decisions.

**`request_id`** (REQUIRED) — Globally unique identifier for the request. MUST be unique across all requests. MUST be treated as immutable. Used for logging and telemetry correlation.

**`timestamp`** (REQUIRED) — Request creation timestamp. Used for logging only. Runtime MUST NOT use this for timeout enforcement or durable ordering. Durable store timestamps remain authoritative.

**`correlation_id`** (OPTIONAL) — Application-level correlation identifier. Runtime MUST pass through unchanged. Runtime MUST NOT require it.

**`trace_id`** (OPTIONAL) — Tracing identifier (OpenTelemetry compatible). Runtime MAY use for tracing. Runtime MUST NOT require it.

**`resume_token`** (OPTIONAL, string) — Opaque token representing prior suspension. If present, indicates this request resumes a suspended execution; runtime MUST validate token against durable thread state and MUST reject invalid or expired tokens. If absent, treated as new phase initiation.

**`input`** — REQUIRED when `resume_token` is null. OPTIONAL when `resume_token` is non-null. Represents user-provided `ContentPart` objects.

**`transport_metadata`** (OPTIONAL) — Opaque JSON payload. May include transport-layer information (headers, etc.). Runtime MUST treat as opaque and MUST NOT depend on it for correctness.

---

## 3. RuntimeResponse (Synchronous)

### Purpose

Represents the terminal result of a synchronous invocation. Exactly one `RuntimeResponse` MUST be returned per invocation.

### Structural Schema

```json
{
  "type": "enum",
  "request_id": "string",
  "thread_id": "string",
  "runtime_key": "string",
  "timestamp": "ISO-8601 string",
  "correlation_id": "string | null",
  "trace_id": "string | null",
  "content": [ "ContentPart" ],
  "resume_token": "string | null"
}
```

### `type` (REQUIRED)

Enum values: `COMPLETE`, `SUSPEND`, `ERROR`

### Outcome Semantics

**`COMPLETE`** — Represents successful execution. Corresponds to durable `AgentOutput`. `content` MUST contain final agent output. `resume_token` MUST be null.

**`SUSPEND`** — Represents suspended execution. Corresponds to durable `SuspendEntry`. `content` MUST explain suspension state and next steps. `resume_token` MUST be present.

**`ERROR`** — Represents execution failure or request rejection. Corresponds to durable `ErrorEntry` or pre-initiation rejection. `content` MUST contain user-facing error information. `resume_token` MUST be null.

### Content Rules

`content` is REQUIRED for ALL response types. All messaging MUST be expressed via `ContentPart`. There is no separate error object.

---

## 4. RuntimeEvent (Streaming)

### Purpose

Represents streaming execution progress. Returned as an `AsyncIterator` when runtime is invoked in streaming mode. Payload structure aligns with `RuntimeResponse`.

### Structural Schema

```json
{
  "type": "enum",
  "request_id": "string",
  "thread_id": "string",
  "runtime_key": "string",
  "timestamp": "ISO-8601 string",
  "correlation_id": "string | null",
  "trace_id": "string | null",
  "content": [ "ContentPart" ] | null,
  "resume_token": "string | null"
}
```

### Event Types

Non-terminal: `START`, `DELTA`

Terminal: `COMPLETE`, `SUSPEND`, `ERROR`

### Event Semantics

**`START`** — Indicates beginning of streaming execution output. Lifecycle enforcement and durable state alignment are defined in the Runtime specification.

**`DELTA`** — Represents incremental streaming content. Typically contains a single `ContentPart` of type `TEXT`. May repeat multiple times.

**`COMPLETE`** (Terminal) — Represents successful execution. Corresponds to durable `AgentOutput`. MUST include final content. MUST NOT include `resume_token`.

**`SUSPEND`** (Terminal) — Represents suspended execution. Corresponds to durable `SuspendEntry`. MUST include `content`. MUST include `resume_token`.

**`ERROR`** (Terminal) — Represents execution failure or request rejection. Corresponds to durable `ErrorEntry` or pre-initiation rejection. MUST include `content`. MUST NOT include `resume_token`.

### Event Rules

- Events MUST be emitted in causal order.
- Exactly one terminal event MUST be emitted.
- No events may follow a terminal event.
- `resume_token` MUST appear only on `SUSPEND`.
- Terminal events MUST include `content`.
- Execution lifecycle enforcement is defined in the Runtime specification.

---

## 5. ResumeToken

### External Representation

`ResumeToken` is represented as an opaque string.

### Internal Logical Structure (Conceptual)

Derived from durable suspend state:

```json
{
  "thread_id": "string",
  "suspend_entry_id": "string",
  "runtime_key": "string",
  "issued_at": "ISO-8601 string",
  "expires_at": "ISO-8601 string"
}
```

### Rules

`ResumeToken`:

- MUST be derived from durable `SuspendEntry`.
- MUST NOT contain `ContentPart`.
- MUST be validated against durable thread state.
- MUST become invalid if: already consumed, expired, mismatched to thread, or mismatched to `runtime_key`.
- ResumeToken validation alone does not guarantee resume permission. Runtime MUST additionally enforce resume authorization via ResumeAuthorizationPolicy as defined in the FlotillaRuntime specification.

Runtime MUST treat the token as opaque except for validation. Implementation MAY encode as a signed token, Base64 JSON, or opaque ID referencing a durable record.


---

## 6. Architectural Guarantees

This I/O model guarantees:

- Transport independence
- Deterministic execution-phase scoping
- Resume safety
- Explicit terminal states
- Streaming parity with sync
- Strict separation from storage semantics
- No embedded concurrency or lifecycle rules