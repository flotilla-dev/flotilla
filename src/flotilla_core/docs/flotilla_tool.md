# FlotillaTool — Behavior & API Design Specification (v2.1)

## 1️⃣ Design Intent

FlotillaTool represents a:

- DI-managed
- Stateless
- LLM-callable capability
- Framework-neutral execution unit

**It encapsulates business logic and exposes a single executable callable for agent/adapters to wrap into library-native tool constructs.**

---

## 2️⃣ Architectural Position

```
FlotillaTool (execution callable)
        ↓
Library-Specific Agent/Adapter (wrap into library tool)
        ↓
LLM / Graph Engine (invokes tool)
        ↓
Agent (decides what becomes externally visible)
        ↓
AgentEvent (agent-only protocol)
        ↓
Runtime (durability boundaries)
```

### Critical Boundary

**Tools:**

- Do NOT emit `AgentEvent`
- Do NOT mutate `ThreadEntry`
- Do NOT know about `ThreadContext` or runtime
- Are internal to agent execution

**Only agent `message_final` mutates thread state.**

---

## 3️⃣ Separation of Concerns

| Layer                        | Responsibility                                                      |
|------------------------------|---------------------------------------------------------------------|
| Tool                         | Business logic + executable callable                                |
| Agent                        | Executes reasoning and decides externally visible output            |
| Adapter / Library Agent      | Wraps the tool callable into library-native tool representation     |
| Runtime                      | Orchestration + durability (persists agent state transitions only)  |

---

## 4️⃣ Public API

### 4.1 Base Class Contract

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable


class FlotillaTool(ABC):
    """
    Framework-neutral tool definition.

    A tool exposes metadata for tool selection and a single executable callable
    that will be wrapped by a library-specific agent/adapter (LangChain, etc.).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @property
    @abstractmethod
    def llm_description(self) -> str:
        """LLM-facing description used for tool selection."""

    @abstractmethod
    def execution_callable(self) -> Callable:
        """
        Return the underlying executable callable.

        The returned callable may be:
          - sync function
          - async function
          - sync generator function
          - async generator function

        Agents/adapters are responsible for wrapping this callable into
        library-native tool constructs and bridging invocation semantics.
        """
```

### Notes

- There is no `id` on the tool
- Uniqueness is achieved by container keys / registration keys (outside tool object)
- Tools are DI-managed instances; the callable may be a bound method

---

## 5️⃣ Statelessness Requirement

**Tools:**

- MUST NOT rely on mutable in-memory state across calls
- MUST accept all required input via callable parameters
- MAY be invoked concurrently
- SHOULD be deterministic for same inputs (unless explicitly performing external I/O)

**Tools may use injected dependencies (clients, repos, configs), but must remain free of per-thread mutable state.**

---

## 6️⃣ Execution Model

The callable returned by `execution_callable()` may be:

- `def f(...) -> Any`
- `async def f(...) -> Any`
- `def f(...) -> Iterator[Any]`
- `async def f(...) -> AsyncIterator[Any]`

**Tool streaming (yielding) is permitted internally, but it is not automatically a protocol feature; the agent decides what becomes externally visible.**

---

## 7️⃣ Output Visibility Model

- Tool outputs are internal intermediate computation
- Tool completion does not change thread state
- Tool output is not persisted as `ThreadEntry`

**The agent may choose to expose tool-derived information via agent `message_*` events, but that is an agent-level concern.**

---

## 8️⃣ Streaming Model

Tools may yield values (generators/async generators). However:

**Tool yields are internal to agent execution.**

The agent may:

- Aggregate tool yields and emit agent `message_final`
- Emit agent `message_chunk` progress derived from tool yields
- Discard intermediate yields

**No tool-specific `message_*` events exist.**

---

## 9️⃣ Adapter / Library-Agent Responsibilities

Library-specific agent/adapters must:

- Wrap `FlotillaTool.execution_callable()` into the library's tool abstraction (e.g., LangChain `StructuredTool`)
- Bridge sync/async invocation correctly
- Handle argument passing and type handling per library needs
- Ensure tool exceptions surface to the agent so the agent can emit `error` (or fail)

### Adapters Must Not

- Modify business logic
- Inject durable state behavior
- Assume tool outputs are externally visible

---

## 🔟 What This Design Intentionally Avoids

- ❌ Tool-level `AgentEvent` emission
- ❌ Tool-level `ThreadEntry` durability
- ❌ Tool lifecycle events
- ❌ Schema enforcement requirements (beyond what a library adapter may infer)
- ❌ Transport contracts inside tool

---

## 1️⃣1️⃣ Example

```python
from typing import Callable, AsyncIterator

class SearchUsersTool(FlotillaTool):
    def __init__(self, repo):
        self.repo = repo

    @property
    def name(self) -> str:
        return "Search Users"

    @property
    def llm_description(self) -> str:
        return "Search users by name."

    def execution_callable(self) -> Callable:
        return self.search

    async def search(self, name: str, limit: int = 20) -> AsyncIterator[dict]:
        async for user in self.repo.stream_users(name, limit):
            yield {"user": user}
```

---

## 🔥 Final Invariant

- **FlotillaTool provides an executable callable + metadata**
- **Tools are internal to agents**
- **Thread state changes only when the agent emits `message_final`, `suspend`, or `error`**