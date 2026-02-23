# Flotilla Thread Model Specification (v3.1)

## 1️⃣ ThreadEntry — Durable Log Record

ThreadEntry represents an immutable, append-only record in a thread.

It is:

- Store-assigned identity
- Store-assigned timestamp
- Deterministic
- Replayable
- Fully auditable

**ThreadEntry represents state transitions, not execution steps.**

## 2 Execution Phase Model

An execution phase begins when a UserInput or ResumeEntry
is appended to the thread.

The phase ends when exactly one of the following entries
is appended:

- AgentOutput
- SuspendEntry
- ErrorEntry

Terminal entries MUST include:

parent_entry_id: str

This MUST reference the entry_id of the initiating
UserInput or ResumeEntry.

All entry_id values are unique.
parent_entry_id establishes causal linkage.

---

## 3 Canonical ThreadEntry Types

### Input

- `UserInput`
- `ResumeEntry`

### Output

- `AgentOutput`

### Execution Control

- `SuspendEntry`
- `ErrorEntry`

### Lifecycle

- `ClosedEntry` (terminal)

**There is no ToolOutput.**

---

## 4 Mapping: AgentEvent → ThreadEntry

| AgentEvent     | ThreadEntry   |
|----------------|---------------|
| message_final  | AgentOutput   |
| suspend        | SuspendEntry  |
| error          | ErrorEntry    |


### Notes

- `ResumeEntry` is appended externally
- `ClosedEntry` is runtime-controlled only
- Only these AgentEvent types produce durable ThreadEntry records.

---

## 5 Execution Phase Termination Entries

There are three entries that can terminate an execution phase:

- AgentOutput
- SuspendEntry
- ErrorEntry

No additional AgentOutput, SuspendEntry, or ErrorEntry may follow for the same parent_entry_id.

All three are durable terminal entries. Each MAY contain:

### Contains

- `content: List[ContentPart]`
- `execution_metadata: Optional[Dict[str, Any]]` (optional JSON-serializable execution telemetry such as token usage, timing, or stack traces)

`execution_metadata` is intended for internal logging, auditing, or telemetry and may not be returned to the end user.

These entries represent the only durable phase termination mutations.

---

## 6 ThreadContext

ThreadContext is an immutable, validated snapshot of ordered ThreadEntry objects.

### It Provides

- Structural validation
- Status derivation
- Protocol invariants
- Convenience accessors

### It Is

- Not mutable
- Not a store
- Not a runtime

---

## 7 Structural Invariants

ThreadContext must validate:

- Non-empty
- All entries share same `thread_id`
- Resume must follow Suspend
- No entries after `ClosedEntry`
- Suspend must be followed by Resume unless it is last entry

---

## 8 Thread Status

Derived from last entry:

| Last Entry    | Status    |
|---------------|-----------|
| SuspendEntry  | SUSPENDED |
| ClosedEntry   | CLOSED    |
| Anything else | RUNNABLE  |

**There is no COMPLETED state.**

**Execution completion does not terminate thread.**

---

## 9 Lifecycle Flow

1. Thread exists (append-only log)
2. Runtime loads entries → builds ThreadContext
3. Runtime invokes Agent
4. Agent emits AgentEvent
5. Runtime maps durable events to ThreadEntry
6. ResumeEntry may be appended
7. ClosedEntry may be appended

**Agents cannot close threads.**

---

## 10 Architectural Guarantees

- ✅ Append-only log
- ✅ Deterministic replay
- ✅ Execution ≠ lifecycle
- ✅ No hidden state
- ✅ Durable boundaries strictly enforced

---

## 11 Related Specifications

- AgentEvent Specification
- ContentPart Specification
- FlotillaAgent Specification