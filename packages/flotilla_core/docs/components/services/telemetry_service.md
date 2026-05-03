# TelemetryService Specification (v3.0)

## 1. Executive Summary

`TelemetryService` defines the framework-wide, pluggable telemetry interface for Flotilla.

It provides structured, non-authoritative observation of selected framework behavior across:

- Runtime execution
- Agent execution
- Suspend / Resume lifecycle
- Timeout enforcement

The initial telemetry taxonomy is intentionally small. Additional event types may be added as framework observability needs become clearer.

`TelemetryService` is injectable across the framework, transport-agnostic, storage-agnostic, observational only, and non-fatal by design.

`TelemetryService` MUST NOT influence execution semantics. Execution correctness is defined by other framework specifications.

---

## 2. Architectural Context

`TelemetryService` is a core collaborator that may be injected into:

- `FlotillaApplication`
- `FlotillaRuntime`
- `FlotillaAgent`
- `FlotillaTool` (optional)
- `SuspendService`
- `ExecutionTimeoutPolicy`

`TelemetryService` does not own execution lifecycle, durability, or concurrency. It observes framework behavior but does not define it.

---

## 3. Core Concepts

`TelemetryService` is a pluggable, best-effort observer. `TelemetryEvent` is the canonical event object passed to the service.

Core terms:

- Telemetry event: structured diagnostic signal emitted by a framework component.
- Context: optional correlation identifiers attached to telemetry.
- Attributes: JSON-safe diagnostic values carried with an event.
- No-op service: default implementation that intentionally drops telemetry.

---

## 4. Responsibilities

`TelemetryService` is responsible for:

- Receiving structured `TelemetryEvent` objects
- Emitting or forwarding those events to an observability backend
- Ensuring telemetry emission is safe and non-disruptive

---

## 5. Non-Responsibilities

`TelemetryService` is NOT responsible for:

- Modifying execution behavior
- Persisting thread entries
- Retrying failed execution
- Enforcing lifecycle rules
- Blocking execution
- Managing spans or traces

---

## 6. Behavioral Contract

### Interface Contract

`TelemetryService` exposes a single method:

```python
class TelemetryService(ABC):

    def emit(self, event: TelemetryEvent) -> None:
        ...
```

The framework invokes `emit()` whenever a telemetry event is generated. Implementations MUST NOT raise exceptions.

### Failure Handling

If `TelemetryService.emit` raises an exception:

- The framework MUST catch and swallow it.
- Execution MUST continue unaffected.
- No execution state may be altered.

Telemetry is strictly non-fatal.

---

## 7. Constraints & Guarantees

`TelemetryService` MUST:

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

**`event_type`** (REQUIRED) — Canonical identifier describing what occurred. Event values use lowercase dotted names in the form `<domain>.<entity>.<outcome>`, such as `runtime.phase.started` or `agent.run.failed`. The framework SHOULD define and maintain a small canonical event taxonomy.

**`component`** (REQUIRED) — Name of the emitting component. Examples: `FLOTILLA_RUNTIME` and `FLOTILLA_AGENT`.

**`timestamp`** (OPTIONAL) — ISO-8601 timestamp indicating when the event was emitted. Defaults to the current UTC time.

**`severity`** (OPTIONAL) — Enum: `DEBUG`, `INFO`, `WARNING`, `ERROR`. Defaults to `INFO`. Reflects observability classification, not execution outcome.

**`context`** (OPTIONAL) — Arbitrary structured identifiers for correlation and trace alignment. Values must be JSON-safe. MUST NOT contain `ContentPart`, secrets, or raw tool payloads.

**`attributes`** (REQUIRED) — Flat JSON-safe key-value map. Used for durations, counters, flags, configuration identifiers, and state indicators. MUST NOT contain sensitive information.

---

## 9. Interaction Model

`TelemetryService` may receive the following current canonical events:

**Runtime Phase**
- `runtime.phase.started`
- `runtime.phase.completed`
- `runtime.phase.suspended`
- `runtime.phase.failed`
- `runtime.thread.not_found`
- `runtime.active_thread.rejected`
- `runtime.resume.rejected`
- `runtime.timeout.closed`

**Agent Phase**
- `agent.run.started`
- `agent.run.completed`
- `agent.run.failed`

Additional detail SHOULD be represented as structured attributes rather than as additional event types. For example, `runtime.resume.rejected` SHOULD use a `reason` attribute such as `invalid_token`, `expired_token`, or `unauthorized`.

---

### Thread Safety and Concurrency

`TelemetryService` implementations MUST:

- Be thread-safe
- Be re-entrant
- Support concurrent invocation

The framework does not guarantee ordering across threads.

---

## 10. Configuration Contract

The framework MUST provide a default no-op implementation:

```python
class NoOpTelemetryService:
    def emit(self, event: TelemetryEvent) -> None:
        pass
```

`TelemetryService` is optional.

---

## 11. Extension Points

`TelemetryService` may be implemented to support structured logging, metrics aggregation, audit logging, distributed tracing adapters, and enterprise observability systems.

Adapters may transform `TelemetryEvent` into logs, metrics, spans, or external telemetry pipelines. The `TelemetryService` interface remains neutral and does not encode tracing semantics.

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
- `SuspendService`
- `ExecutionTimeoutPolicy`
- `Runtime I/O`
