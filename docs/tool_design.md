# FlotillaTool — Behavior & API Design Summary (vNext Draft)

## 1. Design Intent

FlotillaTool represents a:

- **DI-managed**
- **Stateless**
- **LLM-callable capability**
- **Framework-neutral**
- **Streaming-capable**

### Developer Experience

Write a single Python method that performs business logic.

- No schema maintenance
- No payload dict plumbing
- No framework coupling

---

## 2. Core Architecture

```
FlotillaTool (identity + DI anchor)
        ↓
Decorated execution method (business logic)
        ↓
Agent (invocation + streaming handling)
        ↓
Framework Adapter (LangChain / Haystack / etc.)
        ↓
Runtime (event streaming via stream())
```

### Separation of Concerns

| Layer   | Responsibility                |
|---------|-------------------------------|
| Tool    | Business logic only           |
| ABC     | Identity + validation         |
| Agent   | Invocation + streaming detection |
| Adapter | Framework integration         |
| Runtime | Event emission                |

---

## 3. Developer-Facing API

### 3.1 Tool Base Class

```python
class FlotillaTool(ABC):

    def __init__(self):
        self._execution_method = self._discover_execution_method()

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique within FlotillaContainer."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @property
    @abstractmethod
    def llm_description(self) -> str:
        """LLM-facing description used for tool selection."""
```

### 3.2 Execution Decorator

```python
def tool_call(func):
    func._is_flotilla_tool_callable = True
    return func
```

#### Rules

- Exactly one `@tool_call` method per tool class
- Must be an instance method
- May be sync or async
- May return:
  - Value
  - Generator
  - Async generator
- Validation occurs inside `FlotillaTool.__init__`

---

## 4. Tool Behavior Rules

### 4.1 Stateless by Design

Tools:

- **MUST NOT** rely on mutable in-memory state across calls
- **MUST** accept all required input via method parameters
- **MUST** return continuation tokens explicitly if needed
- **MAY** be invoked concurrently

#### Pagination Example Pattern

```python
@tool_call
async def search(name: str, cursor: str | None = None):
    ...
    return {
        "results": [...],
        "next_cursor": ...
    }
```

#### Streaming Version

```python
@tool_call
async def search(name: str, cursor: str | None = None):
    async for user in ...:
        yield user
```

### 4.2 Execution Model

Tool execution method may be:

- Sync function
- Async function
- Sync generator
- Async generator

**The tool does not know about:**

- Runtime
- Event system
- Framework adapters
- Streaming orchestration

It simply returns or yields values.

---

## 5. Agent Invocation Contract

The Agent is responsible for:

- Calling the tool method
- Detecting result type
- Emitting structured events
- Handling errors

### Invocation Logic

```python
result = method(**kwargs)

if inspect.iscoroutine(result):
    result = await result

if inspect.isasyncgen(result):
    async for item in result:
        yield ToolEvent(item)

elif inspect.isgenerator(result):
    for item in result:
        yield ToolEvent(item)

else:
    yield ToolEvent(result)
```

---

## 6. Streaming Behavior

Streaming is supported natively via Python generators.

Tool may:

- Yield partial results
- Yield structured events
- Yield progress markers
- Yield summary objects

The runtime's `stream()` method emits these as events.

**No special streaming interface is required.**

---

## 7. Adapter Responsibilities

Framework adapters:

- Extract execution method
- Inspect signature
- Detect async vs sync
- Create framework-compatible tool
- Handle invocation bridging

### Adapters Must Not

- Modify tool logic
- Enforce schema
- Inject business behavior

**The adapter is a thin wrapper.**

---

## 8. Runtime Responsibilities

`FlotillaRuntime.stream()`:

- Delegates to agent execution stream
- Emits events outward
- Remains agnostic to tool internals

### Runtime Does Not

- Inspect tool implementation
- Manage tool concurrency
- Interpret tool payloads

---

## 9. Validation Rules

Validation occurs inside `FlotillaTool.__init__`.

### Rules Enforced

- Exactly one `@tool_call` method
- Method must be bound to instance
- `id` must be unique within container (container-level validation)

**The container does not inspect tool structure.**

---

## 10. What This Design Intentionally Avoids

- ❌ No JSON schema enforcement
- ❌ No payload dict abstraction
- ❌ No `execute()` / `aexecute()` naming convention
- ❌ No framework-specific subclasses
- ❌ No required metadata models
- ❌ No transport contracts
- ❌ No output validation system

---

## 11. Strengths of This Model

- ✅ Developer-friendly
- ✅ Pythonic
- ✅ Reflection-compatible (LangChain)
- ✅ Async-native
- ✅ Streaming-native
- ✅ Stateless cloud-safe
- ✅ DI-compatible
- ✅ Framework-neutral
- ✅ Minimal surface area

---

## 12. Known Tradeoffs (Accepted)

- No static enforcement of argument shape
- No built-in schema generation
- Tool authors must document parameters clearly
- Adapter must handle reflection carefully

**These are intentional to preserve simplicity.**

---

## 13. Example — Full Tool Lifecycle

```python
class SearchUsersTool(FlotillaTool):

    def __init__(self, repo):
        self.repo = repo
        super().__init__()

    @property
    def id(self):
        return "search_users"

    @property
    def name(self):
        return "Search Users"

    @property
    def llm_description(self):
        return "Search users by name and stream results."

    @tool_call
    async def search(self, name: str, limit: int = 20):
        async for user in self.repo.stream_users(name, limit):
            yield user
```

### Execution Flow

1. Container instantiates tool
2. ABC validates decorated method
3. Agent retrieves execution callable
4. Adapter wraps for LangChain
5. LLM invokes tool
6. Tool streams results
7. Agent emits `ToolEvent` per yield
8. `Runtime.stream()` emits events outward

---

## 14. Design Philosophy Snapshot

### FlotillaTool Is

A lightweight DI-anchored wrapper around a Python callable.

### Not

- A schema system
- A transport contract
- A framework extension
- A tool registry protocol

**Keep it simple. Let Python do the heavy lifting.**