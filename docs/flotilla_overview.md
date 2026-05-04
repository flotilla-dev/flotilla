# Flotilla Overview and Onboarding

## 1. Executive Summary

Flotilla is a production runtime for AI agent services. It provides the service-layer architecture needed to turn agentic workflows into durable, auditable, resumable systems that can operate inside enterprise software environments.

Most agent frameworks make it easy to invoke a model, call tools, and assemble a demonstration workflow. They typically leave harder production concerns to the application team: durable execution state, human-in-the-loop pause and resume behavior, concurrency control, audit history, lifecycle management, operational boundaries, and integration into existing service architectures. These concerns are not incidental in enterprise systems; they are often the difference between a prototype and a deployable service.

Flotilla is designed for the layer around agent execution. It does not replace agent execution libraries such as LangChain, LangGraph, Haystack, or direct model SDK usage. Instead, it provides a runtime boundary, durable thread model, orchestration contract, configuration and dependency composition model, and adapter surface that allow those execution technologies to be used in production-oriented applications.

The primary problems Flotilla solves are:

- Durable state: agentic workflows are represented as persisted thread logs, allowing execution history to survive process restarts, retries, and multi-request workflows.
- Suspend and resume: workflows can intentionally pause, return a resume token, and continue later after human approval, external input, or delayed business events.
- Auditability: execution phases produce durable terminal records, making workflow outcomes traceable and reconstructable from authoritative state.

The target users of Flotilla are engineering teams building AI-enabled services that need reliability, operational clarity, and integration with existing application infrastructure. Technical leaders should view Flotilla as a runtime foundation for agent-centric services rather than as a prompt framework or model abstraction.

## 2. Architectural Context

Flotilla fits naturally into a microservices architecture as a standalone agent workflow service. In that model, existing services call Flotilla through a transport boundary such as HTTP, streaming HTTP, CLI, message-driven integration, or a custom adapter. The Flotilla-based service owns agent workflow execution, durable thread state, suspend/resume semantics, and runtime orchestration, while surrounding services continue to own domain data, authentication, business APIs, user interfaces, and system-of-record responsibilities.

A typical deployment can be understood as:

```text
User Interface / Business Service / Event Consumer
        |
        v
Transport Adapter
HTTP, CLI, worker, or other application boundary
        |
        v
Application Handler
Creates threads, builds RuntimeRequest, maps domain identity
        |
        v
FlotillaRuntime
Coordinates execution phase and durable state transitions
        |
        +--------------------+
        |                    |
        v                    v
ThreadEntryStore       OrchestrationStrategy
Durable log            Agent execution topology
        |                    |
        v                    v
SQL / durable store     Agents, tools, LLMs, external APIs
```

This shape keeps Flotilla behind a clear service boundary. Existing microservices do not need to know how an agent reasons or how a suspend token is generated; they only need to call the workflow service, receive completion, suspend, or error outcomes, and react according to their domain needs.

Flotilla can also be embedded inside an existing Python service when that is the simpler deployment model. The current configuration and container system is designed for composed applications and may not be required for every embedded use case. `FlotillaRuntime` itself is the core runtime object and can be used directly when an application wants explicit construction rather than declarative Flotilla configuration.

System ownership should be drawn carefully:

- Flotilla owns runtime execution semantics, durable thread execution history, suspend/resume validation flow, orchestration boundaries, and runtime I/O contracts.
- Application services own domain models, business authorization, end-user identity, API design, user experience, and system-of-record data.
- Agent execution libraries own model-specific agent behavior, prompt execution, tool-calling strategies, and model provider integration.
- Infrastructure owns databases, queues, observability backends, deployment topology, and secrets management.

The repository includes example applications that show how Flotilla can be used in practice. The weather example demonstrates a simpler application shape. The loan approval example demonstrates a fuller stack across core runtime, SQL-backed persistence, LangChain integration, and FastAPI integration, including workflow suspension and later resumption.

## 3. Goals

Flotilla is intended to provide a reusable production runtime for agent services with explicit contracts and operationally visible behavior.

Primary goals include:

- Preserve durable workflow state through an append-only thread model.
- Support intentional suspend/resume workflows for human-in-the-loop and long-running processes.
- Make execution auditable by reconstructing workflow state from durable thread entries.
- Keep runtime orchestration separate from agent reasoning and tool business logic.
- Support synchronous and streaming execution through stable runtime I/O objects.
- Allow application teams to use preferred agent execution libraries through adapters and orchestration strategies.
- Provide deterministic application composition through configuration loading, component compilation, dependency injection, and lifecycle management.
- Integrate cleanly with common service transports such as FastAPI without making transport semantics part of the core runtime.

Success for these goals means application teams can build agentic workflows without repeatedly solving durability, concurrency, resume safety, and audit history from scratch.

## 4. Non-Goals

Flotilla is not intended to be a model orchestration library, prompt framework, or replacement for agent execution systems. It should not compete with libraries whose main responsibility is model invocation, graph execution, retrieval, prompt management, or tool selection.

Flotilla does not own application authentication, domain authorization, business data storage, user interface behavior, external notification delivery guarantees, or domain-specific tool implementation. It provides hooks and boundaries where these concerns can be integrated, but those concerns remain application-owned.

## 5. Core Capabilities

Flotilla is organized around a small set of core capabilities that work together to provide production-grade agent execution.

Runtime orchestration is the central execution capability. `FlotillaRuntime` accepts a `RuntimeRequest`, loads durable thread state, creates an immutable phase context, appends the initiating entry for the execution phase, invokes orchestration, streams non-terminal events where applicable, and persists exactly one terminal outcome.

Durable thread state provides the authoritative execution history. `ThreadEntryStore` creates durable thread identities, loads entries in strict order, and appends immutable entries using compare-and-swap predicates. `ThreadContext` is reconstructed from the durable log and is the only authoritative representation of workflow state.

Suspend and resume enables long-running and human-in-the-loop workflows. A workflow can terminate a phase with a durable `SuspendEntry`, return a resume token, and later accept a resume request. Resume validation is delegated to resume handling components before a new `ResumeEntry` is appended.

Agent orchestration defines how runtime delegates execution. `OrchestrationStrategy` receives immutable thread and phase context, coordinates one or more agents, and yields canonical `AgentEvent` objects. Strategies and agents do not perform durable mutations directly.

Application composition provides deterministic construction through Flotilla's internal IoC container. `FlotillaContainer` manages dependency injection, validates component relationships before runtime execution, coordinates lifecycle startup and shutdown, and supports multiple configuration sources with secret resolution before the container is built.

Adapters connect Flotilla to external frameworks. The FastAPI integration, for example, provides HTTP route binding and DI-managed handlers while preserving FastAPI ownership of HTTP semantics and Flotilla ownership of runtime semantics.

## 6. High-Level Architecture

Flotilla uses a layered architecture with strict responsibility boundaries. The runtime is intentionally stateless between requests; durable state lives in the thread store, and execution semantics are derived from the reconstructed thread context.

At a high level, a new execution phase works as follows:

1. An application creates or obtains an existing durable thread identity.
2. The application builds a `RuntimeRequest` with thread id, requesting user, input content, optional metadata, and optional resume token.
3. `FlotillaRuntime` is called with the new `RuntimeRequest`
4. The durable thread state, known as the `ThreadContext`, is loaded from the `ThreadEntryStore`.
5. The user input is appened to the `ThreadContext` and is made available for agent consumption
6. `FlotillaRuntime` invokes `OrchestrationStrategy` with the updated `ThreadContext`
7. One or more `FlotillaAgent` implementation(s) invoke a LLM and associated tools to execute the Agentic logic
8. Agents emit `AgentEvent` that contain progress or termination of the workflow execution.
9. The `FlotillaRuntime` converts the terminal event into one durable `ThreadContext` entry
10. Runtime returns a `RuntimeResponse` or `RuntimeEvent` based on if the client desired a streamed response

The append-only thread log is the foundation of Flotilla's reliability model. Entries are immutable, ordered per thread, assigned store-authoritative identifiers and timestamps, and appended only when the caller's expected previous entry matches the current thread tail. This compare-and-swap behavior prevents stale writers from silently corrupting workflow state and gives the runtime a clear concurrency primitive.

Suspend/resume follows the same durable model. When an agent or orchestration strategy emits a suspend event, runtime appends a durable `SuspendEntry`, reloads the thread context, creates a resume token, and returns a suspend outcome. A configured `SuspendService` may perform best-effort notification or routing, but it does not mutate durable state and cannot change the execution outcome. Later, a resume request must validate the resume token and referenced suspend entry before runtime appends a new `ResumeEntry`.

This architecture is deliberately composable. Agents, tools, orchestration strategies, persistence implementations, transport adapters, and telemetry components can evolve independently as long as they honor the runtime contracts.

## 7. Technology Strategy

Flotilla is implemented as a Python framework with a package structure that separates core runtime behavior from integrations:

- `flotilla_core` contains runtime contracts, thread models, orchestration interfaces, configuration, dependency injection, policies, and services.
- `flotilla_sql` provides SQL-backed implementations for durable persistence.
- `flotilla_langchain` provides adapter integration with LangChain-based agent execution.
- `flotilla_fastapi` provides FastAPI transport and application integration.
- `flotilla_testing` provides shared testing support and behavioral contracts.
- `example_apps` contains reference applications that demonstrate end-to-end usage.

The core technology strategy is to keep Flotilla framework-agnostic at the runtime boundary. Agent execution libraries can be integrated through adapters and orchestration strategies without coupling core thread durability or runtime semantics to a single model framework.

Configuration is declarative but not mandatory for every use case. The configuration system supports YAML and Python composition, validates references and cycles before runtime execution, and coordinates lifecycle-aware components. For embedded or advanced use cases, applications can construct and use `FlotillaRuntime` directly.

Near-term direction should continue to reinforce the same architecture: core runtime stabilization, stronger suspend/resume examples, SQL-backed durable state, FastAPI integration, improved onboarding, and clearer public documentation. Because Flotilla is pre-1.0, APIs and package boundaries may evolve, but the central design intent is stable: durable execution, explicit runtime contracts, suspend/resume workflows, and clean separation between runtime, agents, tools, state, and transport.

## 8. Cross-Cutting Concerns

Reliability is built around durable state and explicit terminal outcomes. Each execution phase should produce exactly one terminal durable entry. Runtime reloads durable state after successful appends rather than relying on assumed in-memory state. Timeout policy can close orphaned active phases lazily on a later invocation.

Concurrency is handled at the durable store boundary. `ThreadEntryStore` uses conditional append predicates to ensure each append extends the current thread tail. Concurrent or stale requests fail rather than producing branching or reordered logs.

Auditability comes from the thread log. Because initiating entries and terminal entries are durable, ordered, and immutable, applications can reconstruct what happened in a workflow from authoritative state. This is especially important for enterprise workflows involving approvals, exception handling, remediation, and regulated decisions.

Security and authorization remain split between application and runtime concerns. Applications own authentication, user identity, tenant boundaries, and domain authorization. Flotilla provides resume authorization hooks so resume behavior can be validated before a suspended workflow continues.

Observability is treated as non-authoritative. Telemetry can record structured runtime activity, but telemetry failure must not affect execution correctness. Durable thread state remains the source of truth.

Transport integration should remain thin. Adapters such as FastAPI translate transport requests into handler calls and handler results into transport responses. They should not redefine runtime state, business logic, or execution semantics.

