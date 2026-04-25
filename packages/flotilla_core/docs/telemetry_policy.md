# TelemetryPolicy Specification (v3.0)

## 1. Executive Summary

`TelemetryPolicy` defines the framework-wide, pluggable telemetry interface for Flotilla.

It provides structured, non-authoritative observation of framework behavior across:

- Configuration loading
- Component compilation
- Container construction
- Runtime execution
- Agent execution
- Tool execution
- Suspend / Resume lifecycle
- Timeout enforcement

`TelemetryPolicy` is injectable across the framework, transport-agnostic, storage-agnostic, observational only, and non-fatal by design.

`TelemetryPolicy` MUST NOT influence execution semantics. Execution correctness is defined by other framework specifications.

---

## 2. Architectural Context

`TelemetryPolicy` is a core collaborator that may be injected into:

- `FlotillaApplication`
- `ConfigLoader`
- `ComponentCompiler`
- `FlotillaContainer`
- `FlotillaRuntime`
- `FlotillaAgent`
- `FlotillaTool` (optional)
- `SuspendPolicy`
- `ExecutionTimeoutPolicy`

`TelemetryPolicy` does not own execution lifecycle, durability, or concurrency. It observes framework behavior but does not define it.

---

## 3. Core Concepts

`TelemetryPolicy` is a pluggable, best-effort observer. `TelemetryEvent` is the canonical event object passed to the policy.

Core terms:

- Telemetry event: structured diagnostic signal emitted by a framework component.
- Context: optional correlation identifiers attached to telemetry.
- Attributes: JSON-safe diagnostic values carried with an event.
- No-op policy: default implementation that intentionally drops telemetry.

---

## 4. Responsibilities

`TelemetryPolicy` is responsible for:

- Receiving structured `TelemetryEvent` objects
- Emitting or forwarding those events to an observability backend
- Ensuring telemetry emission is safe and non-disruptive

---

## 5. Non-Responsibilities

`TelemetryPolicy` is NOT responsible for:

- Modifying execution behavior
- Persisting thread entries
- Retrying failed execution
- Enforcing lifecycle rules
- Blocking execution
- Managing spans or traces

---

## 6. Behavioral Contract

### Interface Contract

`TelemetryPolicy` exposes a single method:

```python
class TelemetryPolicy(Protocol):

    def emit(self, event: TelemetryEvent) -> None:
        ...
```

The framework invokes `emit()` whenever a telemetry event is generated. Implementations MUST NOT raise exceptions.

### Failure Handling

If `TelemetryPolicy.emit` raises an exception:

- The framework MUST catch and swallow it.
- Execution MUST continue unaffected.
- No execution state may be altered.

Telemetry is strictly non-fatal.

---

## 7. Constraints & Guarantees

`TelemetryPolicy` MUST:

- Never mutate framework state.
- Never modify `RuntimeRequest` or `RuntimeResponse`.
- Never access `ThreadEntryStore`.
- Never alter control flow.
- Never throw exceptions into calling component.
- Never block execution.
- Be safe to disable entirely.

Framework components MUST:

- Swallow telemetry failures.
- Treat telemetry as best-effort.
- Never rely on telemetry for correctness.

---

## 8. Observability

### TelemetryEvent Model

### Structural Schema

```json
{
  "event_type": "string",
  "component": "string",
  "timestamp": "ISO-8601 string",
  "severity": "enum",
  "context": { "...": "..." },
  "attributes": { "...": "..." }
}
```

---

### Field Definitions

**`event_type`** (REQUIRED) — Canonical identifier describing what occurred. Examples: `CONFIG_LOAD_START`, `CONFIG_LOAD_COMPLETE`, `COMPILATION_START`, `COMPILATION_COMPLETE`, `CONTAINER_BUILD_START`, `CONTAINER_BUILD_COMPLETE`, `RUNTIME_REQUEST_RECEIVED`, `RUNTIME_PHASE_INITIATED`, `AGENT_RUN_START`, `AGENT_RUN_COMPLETE`, `TOOL_EXECUTION_START`, `TOOL_EXECUTION_COMPLETE`, `RUNTIME_TERMINAL`, `EXECUTION_TIMEOUT_TRIGGERED`. The framework SHOULD define and maintain a canonical event taxonomy.

**`component`** (REQUIRED) — Name of the emitting component. Examples: `ConfigLoader`, `ComponentCompiler`, `FlotillaContainer`, `FlotillaRuntime`, `FlotillaAgent`, `FlotillaTool`, `SuspendPolicy`, `ExecutionTimeoutPolicy`.

**`timestamp`** (OPTIONAL) — ISO-8601 timestamp indicating when the event was emitted. Defaults to the current UTC time.

**`severity`** (OPTIONAL) — Enum: `DEBUG`, `INFO`, `WARN`, `ERROR`. Defaults to `INFO`. Reflects observability classification, not execution outcome.

**`context`** (OPTIONAL) — Arbitrary structured identifiers for correlation and trace alignment. Values must be JSON-safe. MUST NOT contain `ContentPart`, secrets, or raw tool payloads.

**`attributes`** (REQUIRED) — Flat JSON-safe key-value map. Used for durations, counters, flags, configuration identifiers, and state indicators. MUST NOT contain sensitive information.

---

## 9. Interaction Model

`TelemetryPolicy` may receive events at various lifecycle boundaries:

**Configuration Phase**
- `CONFIG_LOAD_START`
- `CONFIG_LOAD_COMPLETE`
- `CONFIG_VALIDATION_ERROR`

**Compilation Phase**
- `COMPILATION_START`
- `COMPILATION_COMPLETE`
- `REF_RESOLUTION`
- `COMPILATION_ERROR`

**Container Build Phase**
- `CONTAINER_BUILD_START`
- `COMPONENT_INSTANTIATED`
- `CONTAINER_BUILD_COMPLETE`

**Runtime Phase**
- `RUNTIME_REQUEST_RECEIVED`
- `RUNTIME_PHASE_INITIATED`
- `AGENT_EVENT_EMITTED`
- `RUNTIME_TERMINAL`
- `RUNTIME_REJECTED`

**Agent Phase**
- `AGENT_RUN_START`
- `AGENT_RUN_COMPLETE`
- `AGENT_RUN_ERROR`

**Tool Execution Phase**
- `TOOL_EXECUTION_START`
- `TOOL_EXECUTION_COMPLETE`
- `TOOL_EXECUTION_ERROR`

---

### Thread Safety and Concurrency

`TelemetryPolicy` implementations MUST:

- Be thread-safe
- Be re-entrant
- Support concurrent invocation

The framework does not guarantee ordering across threads.

---

## 10. Configuration Contract

The framework MUST provide a default no-op implementation:

```python
class NoOpTelemetryPolicy:
    def emit(self, event: TelemetryEvent) -> None:
        pass
```

`TelemetryPolicy` is optional.

---

## 11. Extension Points

`TelemetryPolicy` may be implemented to support structured logging, metrics aggregation, audit logging, distributed tracing adapters, and enterprise observability systems.

Adapters may transform `TelemetryEvent` into logs, metrics, spans, or external telemetry pipelines. The `TelemetryPolicy` interface remains neutral and does not encode tracing semantics.

---

### Architectural Guarantees

This specification guarantees:

- Framework-wide telemetry consistency
- Zero coupling to transport layer
- Zero coupling to storage layer
- Zero coupling to tracing standards
- Deterministic execution regardless of telemetry presence
- Clean separation between execution and observation

## 12. Related Specifications

- `FlotillaRuntime`
- `FlotillaAgent`
- `FlotillaTool`
- `SuspendPolicy`
- `ExecutionTimeoutPolicy`
- `Runtime I/O`
