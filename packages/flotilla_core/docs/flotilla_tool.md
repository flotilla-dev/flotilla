# FlotillaTool Specification (v2.1)

## 1. Executive Summary

### Purpose

FlotillaTool represents a:

- Dependency-injection managed
- Stateless
- LLM-callable
- Framework-neutral execution unit

It encapsulates business logic and exposes a single executable callable. This callable is wrapped by a library-specific agent or adapter (e.g., LangChain, Haystack) into a library-native tool construct.

FlotillaTool exists to provide a strict boundary between:

- Business logic execution
- Agent reasoning
- Runtime durability
- Library integration

It explicitly does **not**:

- Emit `AgentEvent`
- Mutate `ThreadEntry`
- Access `ThreadContext`
- Persist state
- Enforce transport or schema contracts
- Participate in durability or orchestration

### Architectural Role

| Property | Value |
|---|---|
| Layer | Execution layer (internal to Agent) |
| Durable | No |
| Persisted | No |
| Library-agnostic | Yes |
| Externally pluggable | Yes (via DI container) |
| Stateless | Yes (required) |
| Deterministic | Expected (for same inputs unless external I/O) |

Deterministic behavior is defined by:

- Callable input parameters
- Injected dependencies
- External I/O behavior (if applicable)

---

## 2. Architectural Context

### Position in Flotilla

FlotillaTool sits beneath the Agent layer and above injected infrastructure dependencies.

Relationship to core systems:

| System | Interaction |
|---|---|
| Thread Model | No direct interaction |
| AgentEvent | Does not emit |
| Runtime | Unknown to tool |
| ContentPart | Not directly produced |
| Checkpointing | Not involved |
| External libraries | Wrapped by adapter |

### Interaction Diagram (Conceptual)

```
UserInput
  → Runtime
    → Agent
      → FlotillaTool.execution_callable
        → (returns data)
      → AgentEvent (message_final / error / suspend)
    → Runtime
      → ThreadEntry
```

### Boundary Ownership

FlotillaTool **owns**:
- Business logic execution

FlotillaTool **must NOT**:
- Cross into durability boundary
- Interpret thread history
- Emit agent protocol events
- Control streaming semantics externally

> Only the Agent determines externally visible state.

---

## 3. Core Concepts

### Base Interface

```python
class FlotillaTool(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def llm_description(self) -> str:
        ...

    @property
    @abstractmethod
    def execution_callable(self) -> Callable:
        ...
```

### Supported Callable Return Types (Closed Set)

| Callable Type | Durable? | Notes |
|---|---|---|
| `def → Any` | No | Sync |
| `async def → Any` | No | Async |
| `def → Iterator[Any]` | No | Sync streaming |
| `async def → AsyncIterator[Any]` | No | Async streaming |

Only these callable forms are supported. No additional lifecycle methods are defined.

---

## 4. Responsibilities

`FlotillaTool` is responsible for:

- Providing a typed, callable capability to agents.
- Returning only supported `ContentPart`-compatible output.
- Remaining stateless across invocations.
- Exposing stable tool identity and schema metadata.

## 5. Non-Responsibilities

`FlotillaTool` is NOT responsible for:

- Appending durable thread entries.
- Emitting runtime events directly.
- Managing agent lifecycle, orchestration, or suspend/resume flow.
- Owning runtime timeout or retry policy.
- Mutating `ThreadContext`.

---

## 6. Behavioral Contract

### Core Lifecycle Rules

A FlotillaTool **MUST** expose:
- `name`
- `llm_description`
- `execution_callable`

- `execution_callable` MUST return a callable.
- The callable MUST accept all required input via parameters.
- The callable MAY be invoked concurrently.
- The tool MUST NOT mutate thread state.
- The tool MUST NOT emit `AgentEvent`.
- The tool MUST NOT access runtime state.
- The tool MUST NOT assume its output is externally visible.
- The tool MAY raise exceptions.
- Tool exceptions MUST propagate to the agent.
- The tool MAY yield intermediate values (if generator).
- EXACTLY ONE callable is exposed per tool instance.

---

### Structural Schema

### Required Properties

| Field | Type | Nullable | JSON-Serializable | Notes |
|---|---|---|---|---|
| `name` | `str` | No | Yes | Human-readable |
| `llm_description` | `str` | No | Yes | LLM-facing |
| `execution_callable` | `Callable` | No | No | Runtime-only |

### JSON Requirements

- Tool metadata must be JSON-serializable.
- The callable itself is not serialized.
- Tools MUST NOT embed unserializable state intended for durability.

### Immutability Constraints

- Tool instances SHOULD be immutable after construction.
- Tools MUST NOT rely on mutable per-thread in-memory state.
- Injected dependencies MAY maintain their own internal state.

### Error Handling

- Tool exceptions MUST propagate to Agent.
- Tool MUST NOT swallow execution errors silently.
- Tool MUST NOT emit durable error records.
- Agent decides whether to emit `error`, `message_final`, or `suspend`.

Fail-fast behavior is expected for:

- Invalid inputs
- Dependency failures
- External API errors

Adapters MUST NOT convert tool failures into durable behavior.

---

## 7. State Model

FlotillaTool produces **no durable mutations**.

It does **NOT**:
- Append `ThreadEntry`
- Emit `AgentEvent`
- Write `ExecutionSnapshot`
- Modify `Checkpoint`

These are the ONLY durable mutations permitted by Flotilla:
- Agent-emitted events handled by Runtime

Tools are excluded from durable boundaries.

---

## 8. Constraints & Guarantees

The following must always hold:

- Tool is stateless across calls.
- Tool execution does not mutate thread state.
- Tool execution does not produce durable entries.
- Tool exposes exactly one execution callable.
- Tool callable accepts all required inputs explicitly.
- Tool output visibility is controlled exclusively by Agent.
- Tool yields are internal to Agent unless surfaced.
- Tool does not reorder or buffer externally.

---

## 9. Extension Points

Subclassing is allowed.

Subclasses **MUST**:
- Implement required abstract methods.
- Preserve statelessness invariant.
- Preserve execution isolation.
- Avoid hidden durability behavior.

Subclasses **MUST NOT**:
- Emit agent events.
- Perform runtime coordination.
- Introduce thread awareness.

Adapters may wrap tools but must not alter business logic.

---

## 10. Observability

Tools **MAY**:
- Log internally
- Emit metrics
- Use injected telemetry dependencies

Tools **MUST NOT**:
- Persist telemetry
- Attach metadata to `ThreadEntry`
- Emit reasoning

Observability MUST NOT alter deterministic behavior.

---

### Ordering Guarantees

Tools:
- MUST execute deterministically given identical inputs (except external I/O)
- MUST NOT reorder internal yields artificially
- MUST NOT buffer externally visible data
- MUST NOT emit partial durable state

If streaming:
- Streaming remains internal to Agent.
- No tool-specific streaming protocol exists.

### Architectural Guarantees

- No hidden durable state
- Strict execution boundary
- Library-agnostic contract
- Deterministic replay at Agent boundary
- Stateless by design
- Internal-only execution
- Durable state controlled exclusively by Agent + Runtime

---

## 11. Related Specifications

- FlotillaAgent Specification
