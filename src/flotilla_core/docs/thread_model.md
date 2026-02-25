# Thread Model Specification (v3.1)

## 1. Executive Summary

### Purpose

The Thread Model defines the durable, append-only log structure for Flotilla threads.

It provides:

- Immutable, replayable execution history
- Deterministic state reconstruction
- Explicit execution phase boundaries
- Causal linkage between input and output
- Auditability and durability guarantees

`ThreadEntry` represents state transitions, not execution steps.

The thread model explicitly does **not**:

- Contain execution logic
- Model streaming events
- Encode tool execution
- Store continuation state
- Perform orchestration
- Interpret content

> Execution lifecycle is modeled by `AgentEvent`. Durable state is modeled by `ThreadEntry`.

### Architectural Role

| Property | Value |
|---|---|
| Layer | Durable thread state layer |
| Durable | Yes |
| Persisted | Yes |
| Library-agnostic | Yes |
| Externally pluggable | No |
| Stateless | `ThreadContext` is immutable |
| Deterministic | Yes (append-only replay model) |

Determinism is defined by:

- Ordered sequence of `ThreadEntry` records
- Immutable content
- Store-assigned identity and timestamps

---

## 2. System Architecture Context

### Position in Flotilla

Thread Model sits beneath:

- `FlotillaRuntime`
- `FlotillaAgent`

It interacts directly with:

- `AgentEvent` (via mapping)
- `ContentPart`
- `ThreadContext`

It does **not** interact with:

- Tool layer
- Reasoning engine
- External libraries

### Interaction Diagram (Conceptual)

```
UserInput → ThreadEntry (durable)
    ↓
Runtime → ThreadContext
    ↓
Agent → AgentEvent
    ↓
Runtime → ThreadEntry (durable append)
```

### Boundary Ownership

Thread Model **owns**:
- Durable append-only log
- Execution phase linkage
- Thread status derivation
- Structural invariants

Thread Model **must NOT**:
- Execute agents
- Interpret reasoning
- Perform streaming
- Persist `AgentEvent` directly

---

## 3. Canonical Types / Interfaces

### Closed Set of ThreadEntry Types

| Type | Durable? | Description |
|---|---|---|
| `UserInput` | Yes | External user input |
| `ResumeEntry` | Yes | External continuation input |
| `AgentOutput` | Yes | Durable agent output |
| `SuspendEntry` | Yes | Durable execution pause |
| `ErrorEntry` | Yes | Durable execution failure |
| `ClosedEntry` | Yes | Explicit thread closure |

Only the above entry types are permitted in the durable thread log. No additional entry types are allowed.

### Content Symmetry Rule

All agent-visible input and output MUST be expressed as `content: List[ContentPart]`. Applies to: `UserInput`, `ResumeEntry`, `AgentOutput`, `SuspendEntry`, and `ErrorEntry`. No alternative payload channels are permitted.

---

## 4. Behavioral Contract

### Execution Phase Model

An execution phase begins when one of the following is appended:

- `UserInput`
- `ResumeEntry`

The phase ends when EXACTLY ONE of the following is appended:

- `AgentOutput`
- `SuspendEntry`
- `ErrorEntry`

Terminal entries MUST include `parent_entry_id` referencing the initiating entry's `entry_id`.

Rules:
- All `entry_id` values MUST be unique.
- `parent_entry_id` establishes causal linkage.
- No additional terminal entries may follow for the same `parent_entry_id`.

### `AgentEvent` → `ThreadEntry` Mapping

| `AgentEvent` | `ThreadEntry` |
|---|---|
| `message_final` | `AgentOutput` |
| `suspend` | `SuspendEntry` |
| `error` | `ErrorEntry` |

Only these `AgentEvent` types produce durable `ThreadEntry` records. `message_start` and `message_chunk` are never persisted.

---

## 5. Structural Schema

### Common Fields (All Entries)

| Field | Type | Required |
|---|---|---|
| `entry_id` | string | Yes |
| `thread_id` | string | Yes |
| `created_at` | timestamp | Yes |
| `type` | enum | Yes |

### Input Entries

`UserInput` and `ResumeEntry`:
- MUST NOT include `parent_entry_id`
- MUST include `content: List[ContentPart]`

### Terminal Entries

`AgentOutput`, `SuspendEntry`, `ErrorEntry`:

Required: `parent_entry_id` (string), `content` (`List[ContentPart]`)

Optional: `execution_metadata` (`Optional[Dict[str, Any]]`)

Rules:
- `execution_metadata` MUST be JSON-serializable.
- `execution_metadata` is telemetry only.
- Metadata exposure to end-user is policy-controlled.

### `ClosedEntry`

- No `parent_entry_id`
- Marks lifecycle termination of thread
- Runtime-controlled only — agents cannot emit

### JSON Requirements

- All entries MUST be JSON-serializable.
- No hidden fields permitted.
- No implicit defaults allowed.
- `ContentPart` must conform to the ContentPart specification.

---

## 6. Durable Mutation Boundaries

The ONLY durable mutations permitted:

- Append `UserInput`
- Append `ResumeEntry`
- Append `AgentOutput`
- Append `SuspendEntry`
- Append `ErrorEntry`
- Append `ClosedEntry`

No in-place modification allowed. No deletion allowed. Append-only invariant is absolute.

---

## 7. Invariants

`ThreadContext` MUST validate:

- Thread is non-empty.
- All entries share same `thread_id`.
- `entry_id` uniqueness.
- `ResumeEntry` must follow `SuspendEntry`.
- No entries after `ClosedEntry`.
- `SuspendEntry` must be followed by `ResumeEntry` unless it is the last entry.
- Input entries MUST NOT include `parent_entry_id`.
- Terminal entries MUST include `parent_entry_id`.
- Exactly one terminal entry per execution phase.
- `parent_entry_id` must reference valid initiating entry.

Each invariant must be directly testable.

---

## 8. Extension & Override Points

`ThreadEntry` type set is closed. No subclassing permitted. New durable entry types require specification revision.

`ThreadContext` may provide convenience accessors but must preserve immutability.

---

## 9. Error Handling Rules

Contract violations include:

- Multiple terminal entries for same `parent_entry_id`
- Missing terminal entry for a phase
- `ResumeEntry` without preceding `SuspendEntry`
- Entry appended after `ClosedEntry`
- `parent_entry_id` referencing invalid entry
- Mixed `thread_id` values
- Non-JSON-serializable content

Violations MUST fail-fast during validation. Silent recovery is forbidden.

---

## 10. Observability & Telemetry

`execution_metadata`:
- May include token usage, timing, stack traces
- Must be JSON-serializable
- Is optional
- Is durable
- Exposure is runtime policy-controlled

Thread model does not interpret metadata.

---

## 11. Ordering Guarantees

- Entries MUST be strictly append-only.
- Order MUST reflect causal execution order.
- No reordering permitted.
- Replay of ordered entries MUST reconstruct identical `ThreadContext`.
- No implicit state reconstruction outside the log.

---

## 12. Architectural Guarantees

- Append-only durable log
- Deterministic replay
- Strict execution/durability separation
- Explicit execution phase modeling
- Causal linkage via `parent_entry_id`
- No hidden continuation state
- Immutable `ThreadContext` snapshot
- Agents cannot close threads
- Execution completion does not imply thread termination

---

## 13. Related Specifications

Only specifications directly interacting with the Thread Model:

- AgentEvent Specification
- ContentPart Specification
- FlotillaAgent Specification