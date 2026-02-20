# Flotilla Execution Model: AgentEvent, ThreadEntry, and ThreadContext

  

## 1️⃣ AgentEvent — Execution Boundary Contract

### Purpose
AgentEvent represents ephemeral execution events emitted by an agent during a single run cycle.

It is:
- Stateless
- Streaming-safe
- Library-agnostic
- The only thing the runtime consumes from the agent
- Not persisted directly

**It models execution lifecycle, not conversation state.**

### Canonical AgentEvent Types
| Type  | Meaning | Persisted? |
|--|--|--|
| message_start | Observability hook | ❌ No |
| message_chunk | Streaming partial output | ❌ No |
| message_final | Atomic output mutation | ✅ Yes (mapped to ThreadEntry) |
| suspend | Execution paused | ✅ Yes |
| error | Execution failure | ✅ Yes |

**There is no `complete` event.**

Execution completion is implicit when the stream ends without `suspend` or `error`.

### Streaming Contract

If an agent emits one or more message_chunk events for a given message_id:

- The concatenation of all message_chunk.content_text values must equal the structured content in message_final.
- message_final must contain the complete canonical content.
- message_chunk is a transport-level optimization only.
- Only message_final is persisted.
- Durable replay depends solely on message_final.
- message_chunk must not introduce or omit content relative to message_final.

### AgentEvent Is NOT

- A thread log
- A state machine
- A conversation object
- A tool lifecycle event
- A thread terminator

**It is strictly an execution stream protocol.**

  

---
## 🔷 2️⃣ ThreadEntry — Durable Thread Log Record

### Purpose
ThreadEntry represents a persisted, immutable record in the thread log.

It is:
- Append-only
- Store-assigned identity (`message_id`)
- Store-assigned timestamp
- Fully auditable
- Deterministic
- Replayable

**Everything that happens in a thread is recorded as a ThreadEntry.**

If it's a ThreadEntry, it goes in the log.

### Canonical ThreadEntry Types

#### Input
-  `UserInput`
-  `ResumeEntry`

#### Output
-  `AgentOutput`
-  `ToolOutput`

#### Execution Control
-  `SuspendEntry`
-  `ErrorEntry`

#### Thread Lifecycle
-  `ClosedEntry` (terminal)

  

### Mapping: AgentEvent → ThreadEntry
| AgentEvent | Resulting ThreadEntry |
|--|--|
| message_final (role=AGENT) | AgentOutput |
| message_final (role=TOOL) | ToolOutput |
| suspend | SuspendEntry |
| error | ErrorEntry |
| stream ends normally | — |

  
-  `ResumeEntry` is created externally (e.g., user approval)
-  `ClosedEntry` is runtime-controlled only


### What ThreadEntry Represents

It is not just "chat".
It represents:

- External input
- Agent reasoning output
- Tool results
- Pauses
- Resumptions
- Failures
- Lifecycle changes

**It is the single source of truth for thread state.**

  
---

## 🔷 3️⃣ ThreadContext — Validated Thread Snapshot

### Purpose

ThreadContext is an immutable wrapper around the ordered ThreadEntry list.

It provides:

- Validation
- State derivation
- Protocol enforcement
- Convenience accessors
- Thread-level invariants

**It is not mutable.**
**It is not a store.**
**It is not a runtime.**
**It is a safe, validated snapshot.**

  

### Core Responsibilities

#### 1️⃣ Validate Structural Invariants

- Non-empty
- All entries share the same `thread_id`
- Suspend must be followed by Resume if it is not the last entry.
- No entries allowed after `ClosedEntry`
- Resume must follow Suspend


#### 2️⃣ Derive Thread Status

Thread status is computed from the last entry:
| Last Entry | Thread Status |
|--|--|
| SuspendEntry | SUSPENDED |
| ClosedEntry | CLOSED |
| anything else | RUNNABLE |


**There is no COMPLETED state.**

Execution completion is not thread termination.

### Why ThreadContext Exists

Instead of this in `run()`:

```python
if  isinstance(entries[-1], SuspendEntry):
...
```

You now have:

```python
if thread.status != ThreadStatus.RUNNABLE:
...
```
  
**This centralizes protocol rules.**

---

## 🔷 4️⃣ How They Work Together

Here's the full flow:

### Step 1️⃣: Thread Exists

Thread log contains ordered ThreadEntry objects.

**Example:**

```
UserInput
AgentOutput
ToolOutput
AgentOutput
```
Runtime loads entries → builds `ThreadContext`.


### Step 2️⃣: Runtime Invokes Agent

```python
agent.run(thread_context, config)
```

Base `run()` checks:

-  `thread.status == RUNNABLE`
- structural invariants valid

Then delegates to `_execute()`.

### Step 3️⃣: Agent Emits AgentEvent
  

During execution:
```
message_chunk
message_chunk
message_final
```

Runtime maps:

-  `message_final` → `AgentOutput`
- If tool output → `ToolOutput`
- If `suspend` → `SuspendEntry`
- If `error` → `ErrorEntry`

Each mapping results in a new ThreadEntry appended to store.

### Step 4️⃣: Execution Ends

Three possible outcomes:

#### A) Normal Completion

- Stream ends → no new control entry
- Thread remains `RUNNABLE`

#### B) Suspend

- Agent emits `suspend` → runtime appends `SuspendEntry`
- Thread status becomes `SUSPENDED`

#### C) Error

- Agent emits `error` → runtime appends `ErrorEntry`
- Thread remains `RUNNABLE` unless runtime later closes it

### Step 5️⃣: Resume

- External system appends `ResumeEntry`
- Thread status returns to `RUNNABLE`
- Agent may be invoked again

### Step 6️⃣: Close Thread (Runtime Only)

- Runtime appends `ClosedEntry`
- Thread status becomes `CLOSED`
- No further execution allowed

**Agents cannot close threads.**

---

## 🔷 5️⃣ Architectural Separation of Concerns
| Concept  | Responsibility  |
|--|--|
| AgentEvent | Execution protocol |
| AgentEvent | Execution protocol |
| ThreadEntry | Durable state log |
| ThreadContext | Thread state validation |
| FlotillaAgent | Stateless reasoning |
| Runtime | Orchestration + persistence |
| Store | Identity + durability |

**No hidden state.**
**No implicit lifecycle.**
**No ambiguous completion semantics.**

---

## 🔷 6️⃣ Key Design Properties

- ✅ Execution completion ≠ thread termination
- ✅ Suspend/Resume are durable
- ✅ ToolOutput is first-class
- ✅ No `complete` event
- ✅ Thread lifecycle owned by runtime
- ✅ Everything visible in log
- ✅ Multi-agent workflows supported
- ✅ Deterministic replay possible
- ✅ Stateless agents
- ✅ Append-only thread model

---

## 🔷 7️⃣ Mental Model

### Think of the Thread As
A deterministic, append-only execution log

### Think of AgentEvent As

A streaming execution interface.

### Think of ThreadContext As

A validated state-machine view of that log.

  

---

  