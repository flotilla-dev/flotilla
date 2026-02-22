# Flotilla Runtime Design Summary

## 1️⃣ Core Philosophy

### FlotillaRuntime Is

- A stateless orchestration engine
- A durability boundary
- An event processor
- A checkpoint manager
- A conversation state owner

### FlotillaRuntime Is NOT

- A reasoning engine
- A policy enforcer
- A workflow DSL
- A stateful object holding execution memory
- A library-specific implementation

**It provides infrastructure. Application developers own behavior.**

---

## 2️⃣ Stateless Runtime Principle

### Runtime Instances Must

- Hold no per-execution mutable state
- Be safe to run on any instance in a cloud environment
- Resume execution solely from durable storage

### All Execution State Lives In

- `ConversationStore`
- `CheckpointStore`

### Runtime Only

- Reads state
- Applies `AgentEvents`
- Writes updated state

### This Enables

- Horizontal scaling
- Multi-instance resume
- Cloud-safe execution

---

## 3️⃣ Canonical Event-Driven Architecture

Execution is entirely event-driven.

**Agent emits:** `AgentEvent`

**Runtime:**

- Applies state mutations
- Delegates checkpointing
- Delegates interrupt handling
- Streams event outward

**Runtime does not mutate state directly except via event application.**

---

## 4️⃣ Conversation State Ownership

`ConversationState` is:

- Runtime-owned
- Append-only
- Multi-actor
- Durable
- Auditable

**Agents never mutate it directly.**

Agents communicate intent via events such as:

- `append_message`
- `llm_message_completed`
- `tool_call_completed`

**Runtime applies those mutations.**

---

## 5️⃣ Checkpoint Model (Not Snapshot)

### Checkpoint Is

- A deterministic resumption marker
- Runtime-generated
- Serializable
- Minimal
- Durable

### Checkpoint Is NOT

- Engine memory dump
- Graph serialization
- Library object persistence

### Checkpoint Contains Only

- `thread_id`
- `runtime_key`
- `agent_id`
- `step`
- `conversation`
- `internal_state` (opaque continuation data)
- `suspended` flag

**It contains only what is required to resume execution safely.**

---

## 6️⃣ CheckpointStrategy (Pluggable)

Runtime delegates persistence timing to:

```
CheckpointStrategy
```

### Strategy Decides

- When to persist
- Which events are boundaries
- Debounce/batch behavior

**Runtime does not hardcode checkpoint logic.**

---

## 7️⃣ InterruptStrategy (Pluggable)

For HITL and coordination events:

```
InterruptStrategy
```

### Runtime Responsibilities

- Recognize `hitl_requested`
- Mark suspended
- Persist checkpoint
- Delegate coordination logic

### InterruptStrategy May

- Notify users
- Publish to queues
- Spawn approval agents
- Apply automated policy

**Runtime remains policy-neutral.**

---

## 8️⃣ Dynamic Runtime Selection

`FlotillaApplication` supports dynamic runtime selection per execution.

- Runtimes are registered in DI container
- Application retrieves runtime by key (string)
- Runtime identity (`runtime_key`) is persisted in checkpoint
- Resume enforces runtime identity match

### This Enables

- Multiple orchestration patterns
- Multi-tenant runtime selection
- Feature-based routing

**Without losing deterministic resume.**

---

## 9️⃣ Runtime Composition Model

There is exactly one root runtime per execution.

However, root runtime may:

- Route to sub-runtimes
- Delegate execution internally
- Compose orchestration strategies

**All execution remains under a single checkpoint domain.**

Nested runtimes do not own independent state stores.

---

## 🔟 Streaming Model

Runtime is streaming-native.

### Flow

```
ExecutionEngine → AdapterEvent → AgentEvent → Runtime → User
```

### Runtime

- Does not buffer tokens
- Forwards streaming events immediately
- Applies state mutations at semantic boundaries
- Checkpoints only at configured boundaries

### Supports

- LLM token streaming
- Tool streaming
- HITL interrupts
- Suspend/resume

---

## 1️⃣1️⃣ Library Agnostic Boundary

Runtime does not know about:

- LangChain
- LangGraph
- Haystack
- Middleware
- Tool schemas

**All library integration lives inside:**

- Agent subclass
- Adapter layer

**Runtime consumes only canonical `AgentEvents`.**

---

## 1️⃣2️⃣ Fail-Fast + Deterministic Startup

- Agents eagerly compile execution engines at startup
- Tool wrapping occurs at construction time
- Misconfiguration fails at application boot
- Runtime never builds graphs at execution time

### This Ensures

- Lower request latency
- Early error detection
- Deterministic execution structure

---

## 1️⃣3️⃣ Architectural Guarantees

The current design guarantees:

- ✅ Stateless runtime instances
- ✅ Durable, serializable checkpoints
- ✅ Deterministic resume across instances
- ✅ Multi-user conversation support
- ✅ Multi-agent orchestration support
- ✅ HITL support
- ✅ Tool streaming support
- ✅ Library neutrality
- ✅ Pluggable durability and interrupt policies
- ✅ Explicit runtime selection

---

## 1️⃣4️⃣ Conceptual Positioning

FlotillaRuntime resembles:

- Temporal-style durable workflow engines
- Event-sourced orchestration systems
- Actor-like stateless execution models

**But is LLM-native and streaming-first.**

