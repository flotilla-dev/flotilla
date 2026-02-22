# FlotillaAgent Specification (v3)

## 1️⃣ Purpose

FlotillaAgent is a stateless execution boundary between:

- ThreadContext (durable log snapshot)
- Reasoning engine (LangChain, etc.)
- AgentEvent protocol

It is:

- Stateless
- Async-only
- Streaming-native
- Library-agnostic

---

## 2️⃣ Public API

```python
async def run(
    self,
    thread: ThreadContext,
    config: ExecutionConfig,
) -> AsyncIterator[AgentEvent]
```

**Single entry point.**

**No separate resume method.**

---

## 3️⃣ Statelessness Contract

### A FlotillaAgent Instance May Hold

- Compiled execution engine
- Wrapped tool definitions
- Static configuration

### It Must Not Hold

- Per-thread mutable state
- Durable memory
- Continuation state
- Conversation mutation logic

**Resume safety is achieved via ThreadContext reconstruction.**

**AgentEvent carries no continuation state.**

---

## 4️⃣ Template Method Structure

### Base Class Defines

```python
async def run(...)
```

### Subclass Implements

```python
async def _execute(...)
```

---

## 5️⃣ Base Class Responsibilities

- Validate `thread.status == RUNNABLE`
- Enforce AgentEvent lifecycle contract
- Enforce ordering invariants
- Forward events immediately
- Prevent illegal event sequences

---

## 6️⃣ Subclass Responsibilities

- Invoke reasoning engine
- Wrap FlotillaTool execution callables
- Normalize output into `List[ContentPart]`
- Emit canonical AgentEvent only

---

## 7️⃣ Tool Handling

FlotillaTool execution is internal.

### Tools

- Do not emit AgentEvent
- Do not mutate ThreadEntry
- Do not stream directly to runtime

**Agent decides what tool-derived data becomes externally visible.**

---

## 8️⃣ ExecutionConfig Handling

### Agent

- Must not mutate config
- Must pass recursion_limit to execution engine
- Must not enforce recursion internally

---

## 9️⃣ Empty Output Rule

If reasoning engine produces no output:

Agent must emit:

```python
message_start
message_final(content=[TextPart("")])
```

**Never emit nothing.**

---

## 🔟 Error Semantics

If execution fails:

- Emit `error`
- Do not emit `message_final`
- Initialization errors must raise at construction (fail-fast)

---

## 1️⃣1️⃣ Cancellation Semantics

If coroutine is cancelled:

- Cancellation propagates
- No additional events emitted
- Runtime handles durability implications

---

## 1️⃣2️⃣ Architectural Guarantees

- ✅ Stateless execution
- ✅ Deterministic replay
- ✅ Strict durable boundaries
- ✅ No hidden continuation state
- ✅ Library-agnostic protocol boundary

---

## 1️⃣3️⃣ Related Specifications

- AgentEvent Specification
- Thread Model Specification
- ContentPart Specification
- FlotillaTool Specification

---

## ✅ Result

You now have:

- ✅ No role field
- ✅ No ToolOutput
- ✅ No duplicate lifecycle descriptions
- ✅ No duplicate durable rules
- ✅ Clear separation of concerns
- ✅ Clean cross-referencing
- ✅ Single source of truth per concept