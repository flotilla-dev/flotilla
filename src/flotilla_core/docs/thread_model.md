# Flotilla Thread Model Specification (v3)

## 1️⃣ ThreadEntry — Durable Log Record

ThreadEntry represents an immutable, append-only record in a thread.

It is:

- Store-assigned identity
- Store-assigned timestamp
- Deterministic
- Replayable
- Fully auditable

**ThreadEntry represents state transitions, not execution steps.**

---

## 2️⃣ Canonical ThreadEntry Types

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

## 3️⃣ Mapping: AgentEvent → ThreadEntry

| AgentEvent     | ThreadEntry   |
|----------------|---------------|
| message_final  | AgentOutput   |
| suspend        | SuspendEntry  |
| error          | ErrorEntry    |
| stream ends    | —             |

### Notes

- `ResumeEntry` is appended externally
- `ClosedEntry` is runtime-controlled only

---

## 4️⃣ AgentOutput

Represents durable agent-visible output.

### Contains

- `content: List[ContentPart]`
- Optional metadata

**AgentOutput is the only durable output mutation.**

---

## 5️⃣ ThreadContext

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

## 6️⃣ Structural Invariants

ThreadContext must validate:

- Non-empty
- All entries share same `thread_id`
- Resume must follow Suspend
- No entries after `ClosedEntry`
- Suspend must be followed by Resume unless it is last entry

---

## 7️⃣ Thread Status

Derived from last entry:

| Last Entry    | Status    |
|---------------|-----------|
| SuspendEntry  | SUSPENDED |
| ClosedEntry   | CLOSED    |
| Anything else | RUNNABLE  |

**There is no COMPLETED state.**

**Execution completion does not terminate thread.**

---

## 8️⃣ Lifecycle Flow

1. Thread exists (append-only log)
2. Runtime loads entries → builds ThreadContext
3. Runtime invokes Agent
4. Agent emits AgentEvent
5. Runtime maps durable events to ThreadEntry
6. ResumeEntry may be appended
7. ClosedEntry may be appended

**Agents cannot close threads.**

---

## 9️⃣ Architectural Guarantees

- ✅ Append-only log
- ✅ Deterministic replay
- ✅ Execution ≠ lifecycle
- ✅ No hidden state
- ✅ Durable boundaries strictly enforced

---

## 🔟 Related Specifications

- AgentEvent Specification
- ContentPart Specification
- FlotillaAgent Specification