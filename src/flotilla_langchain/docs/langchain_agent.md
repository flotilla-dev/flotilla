# LangChainAgent Behavior Specification (v2)

## 1️⃣ Architectural Role

LangChainAgent is a concrete subclass of FlotillaAgent that:

- Consumes ThreadContext
- Emits canonical AgentEvent
- Uses a LangGraph CompiledStateGraph internally
- Performs no persistence
- Performs no lifecycle mutation
- Holds no continuation state
- Emits only valid AgentEvent types

**It is a pure adapter between LangChain/LangGraph and Flotilla.**

---

## 2️⃣ Construction Behavior

### Constructor MUST Accept

- `llm`
- `system_prompt: Optional[str]`
- `tools: Optional[List[FlotillaTool]]`
- `model_kwargs: Optional[Dict[str, Any]]`

### Constructor MUST

- Call `_build_graph()` exactly once
- Store compiled graph in `self._graph`
- Fail fast if `_build_graph()` raises
- Not depend on ThreadContext
- Not perform execution during construction

---

## 3️⃣ Graph Customization Plane

### _build_graph()

- Returns `CompiledStateGraph`
- Must be side-effect free
- Must not depend on ThreadContext
- May be overridden by subclasses
- Base class provides a default implementation

**Subclasses are encouraged to override `_build_graph()` to customize graph construction while preserving the base class execution lifecycle, streaming contract, and normalization behavior.**

**Advanced subclasses may override `_execute()` directly if deeper control is required. Doing so transfers responsibility for maintaining compliance with the AgentEvent contract to the subclass implementation.**

---

## 4️⃣ Execution Model

### Invocation

`_execute()` MUST:

- Invoke the compiled graph asynchronously
- Always use streaming mode
- Never provide synchronous execution path

Non-streaming behavior is represented by emitting:

```
message_start
message_final
```

without prior `message_chunk`.

---

## 5️⃣ Allowed AgentEvent Emissions

LangChainAgent may emit only:

- `message_start`
- `message_chunk`
- `message_final`
- `suspend`
- `error`

### There Is

- No role field
- No tool events
- No complete event
- No continuation state

**LangChainAgent MUST obey the AgentEvent Specification.**

---

## 6️⃣ Tool Integration

### Tool Wrapping Contract

Each FlotillaTool MUST be wrapped into a LangChain-compatible tool.

The wrapper MUST:

- Call `FlotillaTool.execution_callable()`
- Preserve tool name and description
- Preserve argument schema
- Not emit AgentEvent
- Not persist state

**Tool execution is internal to the graph.**

### Tool Visibility Model

Tool outputs:

- Are internal intermediate computation
- Do not generate AgentEvent directly
- Do not create ThreadEntry
- May influence agent output

**The agent decides what tool-derived information becomes externally visible.**

---

## 7️⃣ Resume Behavior

If the last durable entry is ResumeEntry:

- LangChainAgent MUST construct a Command
- Resume payload MUST be passed into graph invocation
- Payload structure is library-dependent
- ResumeEntry is not converted into a LangChain message
- No continuation state is stored in AgentEvent

**Resume is reconstruction, not rehydration.**

---

## 8️⃣ System Prompt Injection

If `system_prompt` is provided:

- Insert as SystemMessage
- Prepend to message list
- Not persisted to thread log
- Applied on every `_execute()` invocation

**This is library-specific behavior.**

---

## 9️⃣ Output Normalization Contract

All model outputs MUST be normalized into `List[ContentPart]`.

### Plain Text

```python
[TextPart(text=...)]
```

### Structured JSON

```python
[JsonPart(data=...)]
```

### File Outputs

Must follow ContentPart file rules (URL + mime_type).

**Unknown output types must raise ValueError.**

---

## 🔟 Error Handling

### If Graph Execution Raises

- Emit `AgentEvent(type="error")`
- Do not emit `message_final`
- `recoverable` defaults to `True`
- Metadata may be included (JSON-serializable only)

### Graph Construction Failures

- Must raise during initialization
- Must not emit AgentEvent

---

## 1️⃣1️⃣ Message ID Rules

`message_id`:

- Must be unique per `_execute()` invocation
- Does not require global uniqueness

---

## 1️⃣2️⃣ Event Ordering

Events must be yielded:

- In causal order
- Without buffering
- Without artificial delay

**LangChainAgent must not reorder events.**

---

## 1️⃣3️⃣ Recursion Limit

`recursion_limit` is provided in ExecutionConfig.

- Enforcement belongs to LangGraph
- LangChainAgent must pass it through
- LangChainAgent must not manage recursion itself

---

## 1️⃣4️⃣ Empty Output Handling

If model produces no output:

Emit:

```
message_start
message_final(content=[TextPart("")])
```

**Never emit nothing.**

---

## 1️⃣5️⃣ Cancellation Semantics

If coroutine is cancelled:

- Cancellation propagates
- No AgentEvent emitted
- Runtime handles durability implications

---

## Summary

LangChainAgent v2 is:

- ✅ Stateless
- ✅ Async-only
- ✅ Streaming-native
- ✅ Tool-wrapping
- ✅ Resume-aware via Command
- ✅ Strict about AgentEvent contract
- ✅ Strict about durable boundaries
- ✅ Strict about ContentPart normalization
- ✅ Runtime-agnostic
- ✅ Role-free
- ✅ Tool-event-free