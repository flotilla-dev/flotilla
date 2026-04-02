# Thread Model Specification (v3.2)

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

### SuspendEntry: `resume_audience`

#### Field Definition

`SuspendEntry` MAY include the following optional field:
```json
{  
 "resume_audience": "string | null"  
}
```

#### Field Semantics

-   Opaque string.
-   JSON-serializable.
-   May contain:
    
    -   Base64-encoded blob
    -   Opaque identifier
    -   Signed audience descriptor
    -   Application-defined metadata
        

Flotilla core MUST treat this field as opaque.

Flotilla MUST NOT interpret, parse, or enforce semantics of `resume_audience` directly.

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

Each adjacent start/terminal pair MUST share identical phase_id.

Phase linkage is derived from adjacency and phase_id.

All `ThreadEntry`, except for the first entry in a Thread, must have a `previous_entry_id` in where the referenced `ThreadEntry` is also part of the same Thread (ie `thread_id` are identical)

Rules:
- First entry MUST be `UserInput`
- First entry MUST have `previous_entry_id = None`
- All `entry_id` values MUST be unique.
- `previous_entry_id` establishes causal linkage.
- Exactly one terminal entry MUST follow each start entry.


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

| Field | Type | Required | Description |
|---|---|---|---|
| `thread_id` | string | Yes | The unique id of the conversation thread|
| `phase_id` | string | Yes | The ID of the execution phase to which this `ThreadEntry` belong |
| `entry_id` | string| No | The unique id of an individual entry assigned by `ThreadEntryStore`, is assigned during append() operation |
| `previous_entry_id` | string| No | The ID of the entry previous to this one in the `ThreadContext` |
| `timestamp` | datetime | No | UTC timestamp assigned by `ThreadEntryStore`, is assigned uring append() operation |
| `content` | List[`ContentPart`] | Yes | The content that defines the state change of the Thread |

### Start Entries (UserInput, ResumeEntry)
- Must incldue a `user_id` field that identifies the user that submmitted the request

### Terminal Entries (AgentOutput, SuspendEntry, ErrorEntry)
- Must incldue a `agent_id` field that identifies the agent that generated the state change


### `ClosedEntry`

- Must contain `previous_entry_id`
- Marks lifecycle termination of thread
- Runtime-controlled only — agents cannot emit
- Can only be initiated by a User

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

- Thread non-empty
- All entries share same `thread_id`
- `entry_id` uniqueness
- Linked-list integrity (`previous_entry_id`)
- Strict alternation (Start → Terminal)
- Adjacent entries share identical `phase_id`
- `SuspendEntry` must be followed by ResumeEntry or ClosedEntry
- No entries after `ClosedEntry`
- Exactly one terminal per phase (enforced structurally)
- Each invariant must be directly testable.

---

## 8. Extension & Override Points

`ThreadEntry` type set is closed. No subclassing permitted. New durable entry types require specification revision.

`ThreadContext` may provide convenience accessors but must preserve immutability.

---

## 9. Error Handling Rules

Contract violations include:

- Two consecutive terminal entries
- Two consecutive start entries
- ThreadContext MAY represent an in-progress phase ending in a start entry.
- `ResumeEntry` without preceding `SuspendEntry`
- Entry appended after `ClosedEntry`
- `previous_entry_id` referencing invalid entry
- Mixed `thread_id` values
- Non-JSON-serializable content

Violations MUST fail-fast during validation. Silent recovery is forbidden.

---


## 10. Ordering Guarantees

- Entries MUST be strictly append-only.
- Order MUST reflect causal execution order.
- No reordering permitted.
- Replay of ordered entries MUST reconstruct identical `ThreadContext`.
- No implicit state reconstruction outside the log.

---

## 11. Architectural Guarantees

- Append-only durable log
- Deterministic replay
- Strict execution/durability separation
- Explicit execution phase modeling
- Structural linkage via `previous_entry_id` and `phase_id`
- No hidden continuation state
- Immutable `ThreadContext` snapshot
- Agents cannot close threads
- Execution completion does not imply thread termination

---

## 12. Related Specifications

Only specifications directly interacting with the Thread Model:

- AgentEvent Specification
- ContentPart Specification
- FlotillaAgent Specification