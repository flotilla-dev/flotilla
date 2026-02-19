# FlotillaAgent Design Summary (Revised)

## 1️⃣ Core Philosophy

### FlotillaAgent Is

- A stateless reasoning interface
- A template-method execution wrapper
- A canonical event producer
- A library-agnostic contract boundary

### FlotillaAgent Is NOT

- A runtime
- A persistence manager
- A conversation state owner
- A checkpoint generator
- A workflow engine

**It is a structured bridge between:**

- Reasoning engines (LangChain, Haystack, etc.)
- The FlotillaRuntime orchestration layer

---

## 2️⃣ Architectural Role

```
FlotillaRuntime
    ↕
FlotillaAgent (template base)
    ↕
Library-Specific Agent (LangChainAgent, HaystackAgent, etc.)
    ↕
LLM Framework / Graph Engine
```

### The FlotillaAgent Base Class Defines

- Lifecycle
- Streaming contract
- Continuation semantics
- Event normalization
- Internal state boundary

**Library-specific agents implement reasoning behavior.**

---

## 3️⃣ Template Method Pattern

FlotillaAgent is a partial base class.

### It Owns

- `run(...)`
- Event normalization
- Step tracking (if applicable)
- Internal state handling
- Canonical `AgentEvent` emission

### It Defines One Major Extension Point

```python
build_execution_engine()
```

**Concrete subclasses override this to construct their reasoning engine.**

---

## 4️⃣ Single Entry Point Execution Model

FlotillaAgent exposes a single method:

```python
async def run(
    self,
    conversation: ConversationState,
    checkpoint: Optional[ExecutionCheckpoint],
    execution_options: ExecutionOptions
) -> AsyncIterator[AgentEvent]
```

**There is no separate `resume()` method.**

### Execution Behavior

- If `checkpoint` is `None` → fresh execution
- If `checkpoint` exists → continuation execution

**The decision to resume is internal to the agent implementation.**

Resume is an execution concern, not a public API concern.

---

## 5️⃣ Resume Semantics (Revised)

Resume works as follows:

1. Runtime loads checkpoint from durable storage
2. Runtime appends any new user/system messages to `ConversationState`
3. Runtime calls `agent.run(...)` with the checkpoint
4. Agent rehydrates internal execution state from `checkpoint.internal_state`
5. Execution continues streaming events

### Key Principles

- Agent does not generate checkpoints
- Agent does not persist state
- Agent does not own conversation
- Checkpoint is runtime-generated
- Checkpoint contains only deterministic continuation data
- Resume is simply continuation within `run()`

---

## 6️⃣ Execution Engine Model

The reasoning engine is:

- Built eagerly at agent construction time
- Library-specific
- Opaque to the runtime
- Deterministic across instances

### The Base Class Does Not Know

- Graph structure
- Pipeline nodes
- Middleware configuration
- Tool wrapping details

### It Only Interacts Via

```python
AsyncIterator[AdapterEvent]
```

---

## 7️⃣ Library-Specific Subclasses

### Examples

- `LangChainAgent`
- `HaystackAgent`

### Responsibilities

- Wrap `FlotillaTool` into library-native tools
- Build compiled graph/pipeline
- Translate library streaming callbacks into `AdapterEvents`
- Translate library interrupts into canonical events
- Rehydrate execution engine using `checkpoint.internal_state`

**The base agent remains library-agnostic.**

---

## 8️⃣ Tool Wrapping

Tool wrapping occurs:

- At agent construction time
- Inside library-specific agent subclasses
- During execution engine compilation

### FlotillaTool Remains

- Library-agnostic
- Exposes only `execution_callable`
- Metadata-only

**Tool schema inference, callback wiring, and middleware integration are adapter responsibilities.**

---

## 9️⃣ Streaming Model

Agent execution is streaming-native.

### Flow

```
Library Engine
    → AdapterEvent
    → AgentEvent
    → Runtime
```

### The Base Class

- Immediately forwards normalized events
- Does not buffer
- Does not reorder
- Maintains canonical event structure

### Streaming Supports

- LLM token streaming
- Tool output streaming
- HITL interrupts
- Suspend/resume continuation

---

## 🔟 Statelessness Principle

### FlotillaAgent Instances May Hold

- Compiled execution engines
- Wrapped tool definitions
- Static configuration

### Must NOT Hold

- Per-thread mutable state
- Conversation state
- Checkpoint data
- Execution-specific memory

### All Execution-Specific State Flows Through

- `checkpoint.internal_state`
- Event emission
- Runtime-managed durable storage

---

## 1️⃣1️⃣ Two-Tier Developer Experience

### 🟢 SimpleAgent Pattern

For most developers:

```python
agent = LangChainSimpleAgent(
    model="gpt-4",
    system_prompt="You are helpful.",
    tools=[...]
)
```

**Internally:**

- Uses library helper (e.g., `create_agent`)
- Builds compiled graph at construction time
- Streams events via base class
- Minimal boilerplate

### 🔵 AdvancedAgent Pattern

For advanced developers:

- Override `build_execution_engine()`
- Provide custom LangGraph graph
- Build Haystack pipeline manually
- Inject custom middleware
- Customize execution flow

**Runtime integration remains unchanged.**

---

## 1️⃣2️⃣ Fail-Fast Design

Execution engine compilation happens eagerly:

- Tool wrapping validated at startup
- Graph compilation validated at startup
- Middleware wiring validated at startup

**Misconfiguration fails application boot, not runtime execution.**

---

## 1️⃣3️⃣ Canonical Contract

The only contract between agent and runtime is:

```python
AsyncIterator[AgentEvent]
```

### Agent Emits Canonical Events Such As

- `llm_token`
- `append_message`
- `tool_call_started`
- `tool_output_chunk`
- `tool_call_completed`
- `hitl_requested`
- `suspend`
- `final_response`
- `error`

**Runtime consumes and applies.**

**No library types cross this boundary.**

---

## 1️⃣4️⃣ Architectural Guarantees

The revised FlotillaAgent design guarantees:

- ✅ Library-agnostic runtime boundary
- ✅ Single execution entry point (`run`)
- ✅ Deterministic resume behavior
- ✅ Streaming-first execution
- ✅ HITL compatibility
- ✅ Tool streaming compatibility
- ✅ Startup-time validation
- ✅ Extensibility for new reasoning libraries
- ✅ Minimal abstraction overhead