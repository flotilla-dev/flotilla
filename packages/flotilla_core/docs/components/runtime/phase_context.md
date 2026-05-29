# PhaseContext and PhaseContextService Specification (v1.0-draft)

## 1. Executive Summary

`PhaseContext` is the immutable execution context for a single runtime phase.

It exists so runtime, orchestration, agents, policies, and services can share stable phase metadata without mutating durable thread state or request input.

`PhaseContextService` is the pluggable boundary responsible for creating `PhaseContext` instances. Implementations may create a minimal context from only the `RuntimeRequest`, or may enrich the context with additional immutable thread-level data such as thread attributes.

## 2. Architectural Context

`PhaseContext` sits beside `ThreadContext` as phase-local execution input.

- `ThreadContext` represents durable thread-entry history.
- `PhaseContext` represents immutable metadata and configuration for the current phase.

`FlotillaRuntime` obtains a `PhaseContext` from `PhaseContextService` before constructing or appending phase entries. The resulting context is passed through runtime execution and may be consumed by agents, policies, and services.

`PhaseContextService` is intentionally pluggable. Implementations are not required to read durable storage. A valid service may create a context using only `RuntimeRequest` fields.

## 3. Core Concepts

### PhaseContext

`PhaseContext` contains phase-level metadata such as:

- `thread_id`
- `phase_id`
- `user_id`
- `correlation_id`
- `trace_id`
- `agent_config`
- optional `thread_attributes`

`thread_attributes`, when present, are exposed as a dictionary keyed by attribute name.

### PhaseContextService

`PhaseContextService` creates a new `PhaseContext` for each runtime phase.

The default implementation may remain storage-independent and produce no `thread_attributes`. Applications may provide an implementation that loads immutable thread attributes and includes them in the context.

## 4. Responsibilities

`PhaseContext` is responsible for:

- Carrying immutable phase metadata.
- Carrying optional immutable execution configuration.
- Carrying optional immutable thread attributes for runtime and agent use.
- Preserving phase identity across all entries and events produced during a phase.

`PhaseContextService` is responsible for:

- Creating one `PhaseContext` per runtime phase.
- Assigning a unique `phase_id`.
- Copying relevant request metadata into the phase context.
- Optionally enriching the phase context with immutable thread attributes.

## 5. Non-Responsibilities

`PhaseContext` is NOT responsible for:

- Persisting durable state.
- Representing durable thread-entry history.
- Enforcing thread lifecycle rules.
- Authorizing access to a thread.
- Mutating thread attributes or agent configuration.

`PhaseContextService` is NOT required to:

- Read durable storage.
- Load thread attributes.
- Validate thread existence.
- Append or mutate `ThreadEntry` objects.

## 6. Behavioral Contract

`PhaseContext` MUST be immutable after construction.

`PhaseContextService.create_phase_context(...)` MUST return a complete `PhaseContext` for the phase. Implementations MAY include thread attributes if they are available and appropriate for the application.

If thread attributes are included, they MUST reflect immutable thread-creation-time attributes. They MUST NOT be loaded from mutable request metadata or post-creation thread updates.

## 7. State Model

`PhaseContext` is a value object. It owns no mutable state and persists nothing.

A new `PhaseContext` is created for each runtime phase. It is discarded after the phase completes.

Thread attributes included in `PhaseContext` are copied into phase-local context as a dictionary and do not become part of `ThreadContext`.

## 8. Interaction Model

Runtime obtains a `PhaseContext` before appending the phase-initiating `ThreadEntry`.

The same `PhaseContext` is passed to:

- `OrchestrationStrategy`
- `FlotillaAgent`
- `ResumeService`
- `ResumeAuthorizationPolicy`
- `SuspendService`
- runtime event factories and telemetry emission

Consumers may read values from the context but MUST NOT mutate it.

## 9. Extension Points

Applications may provide a custom `PhaseContextService` to:

- Use application-specific phase identifiers.
- Add agent configuration.
- Include immutable thread attributes.
- Derive runtime configuration from application context.

Storage-aware enrichment is optional and belongs to the custom service implementation.

## 10. Constraints & Guarantees

- `PhaseContext.phase_id` MUST uniquely identify the phase.
- `PhaseContext.thread_id` MUST identify the thread targeted by the runtime request.
- `PhaseContext` MUST be immutable after construction.
- `thread_attributes` MUST be optional.
- A `PhaseContext` with no thread attributes is valid.
- Thread attributes included in a `PhaseContext` MUST be treated as immutable configuration.

## 11. Related Specifications

- [FlotillaRuntime](flotilla_runtime.md)
- [Runtime I/O](runtime_io.md)
- [Thread Model](../thread/thread_model.md)
- [ThreadEntryStore](../thread/thread_entry_store.md)
- [FlotillaAgent](../agents/flotilla_agent.md)
