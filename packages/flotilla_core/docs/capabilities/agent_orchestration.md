# Agent Orchestration Capability Specification (v1.0-draft)

## 1. Executive Summary

Agent Orchestration is how agentic tasks are executed within Flotilla.

When a developer wants Flotilla to do agentic work, they create or obtain a thread, build a `RuntimeRequest`, and submit that request to `FlotillaRuntime`. Runtime then turns that request into a durable execution phase: it records the caller input, reconstructs the current thread context, invokes orchestration, receives agent events, persists the terminal outcome, and returns caller-visible output.

The main developer-facing object is `FlotillaRuntime`. It exposes:

- `run()`, for synchronous execution that returns a single `RuntimeResponse`
- `stream()`, for streaming execution that yields `RuntimeEvent` objects

The main input object is `RuntimeRequest`. It identifies the existing thread, requesting user, optional resume token, input content, and correlation metadata.

The main output objects are:

- `RuntimeResponse`, returned by synchronous execution
- `RuntimeEvent`, yielded during streaming execution
- `ResumeToken`, returned when execution suspends and later supplied on a resume request

Behind that API, this capability coordinates `ThreadEntryStore`, `ThreadContext`, `OrchestrationStrategy`, `FlotillaAgent`, `AgentEvent`, resume handling, timeout policy, suspend handling, and telemetry. Developers use this capability when they want Flotilla to manage the lifecycle of an agentic task rather than manually coordinating persistence, concurrency, resume safety, and terminal outcomes.

## 2. Capability Context

Agent Orchestration sits between external callers and the durable thread model.

The capability includes thread preparation and runtime execution. A durable thread identity MUST exist before a caller submits a `RuntimeRequest`, but `FlotillaRuntime` itself consumes an existing `thread_id`; it MUST NOT implicitly create a thread from a runtime request.

Primary entry points:

- `FlotillaRuntime.run(request: RuntimeRequest) -> RuntimeResponse`
- `FlotillaRuntime.stream(request: RuntimeRequest) -> AsyncIterator[RuntimeEvent]`

Primary durable boundary:

- `ThreadEntryStore`

Primary execution contributor:

- `OrchestrationStrategy`, which may invoke one or more `FlotillaAgent` instances or nested strategies.

## 3. Outcomes

Agent Orchestration must produce one of the following caller-visible outcomes:

- `COMPLETE`: execution finished successfully and produced final output.
- `SUSPEND`: execution paused and produced a resume token.
- `ERROR`: execution failed or the request was rejected.

The capability must also preserve these system outcomes:

- Durable thread state remains authoritative.
- Runtime output reflects durable terminal state when terminal state is produced.
- Concurrent requests against the same thread are rejected or resolved through CAS behavior.
- Resume requests are validated against durable suspend state before new execution begins.
- Timeout handling closes orphaned active phases lazily on the next runtime invocation.

## 4. Scope

This capability includes:

- Creating durable thread identities before runtime execution.
- Accepting runtime requests for existing threads.
- Creating immutable phase context for each request.
- Loading durable thread state.
- Validating active, suspended, closed, or missing thread state.
- Applying timeout policy for active phases.
- Validating resume tokens and authorization for resume requests.
- Appending phase-initiating entries.
- Invoking orchestration strategies.
- Translating agent events into runtime events and durable terminal entries.
- Emitting synchronous runtime responses or streaming runtime events.
- Creating resume tokens after suspend.
- Emitting telemetry where configured.

## 5. Out of Scope

This capability does not:

- Define external transport protocols.
- Define application authentication.
- Define business-domain authorization beyond resume authorization hooks.
- Implement agent reasoning.
- Implement tool business logic.
- Persist non-terminal streaming output.
- Guarantee delivery of external suspend notifications.
- Define UI behavior for suspend, resume, error, or completion states.

## 6. Execution Workflow

### Thread Preparation

1. A caller or application service creates a thread through the thread lifecycle surface.
2. The created `thread_id` is returned to the caller or retained by the application.
3. The caller includes that existing `thread_id` in a `RuntimeRequest`.

Runtime execution MUST fail if the submitted `thread_id` does not identify an existing thread.

Thread creation is part of the Agent Orchestration capability because every agentic task needs a durable thread identity. It is separated from `FlotillaRuntime.run()` and `FlotillaRuntime.stream()` so runtime execution remains explicit: requests always target known threads.

### New Execution Phase

1. Caller submits a `RuntimeRequest` without `resume_token`.
2. `FlotillaRuntime` creates a `PhaseContext`.
3. Runtime loads durable entries from `ThreadEntryStore`.
4. Runtime reconstructs `ThreadContext`.
5. If the thread is actively running, runtime evaluates timeout policy.
6. If no blocking condition exists, runtime appends a `UserInput` entry using CAS.
7. Runtime reloads durable state and reconstructs `ThreadContext`.
8. Runtime invokes `OrchestrationStrategy`.
9. `OrchestrationStrategy` coordinates agent execution and yields canonical `AgentEvent` objects.
10. Runtime streams non-terminal events as `RuntimeEvent` objects without durable mutation.
11. Runtime converts exactly one terminal `AgentEvent` into a durable terminal `ThreadEntry`.
12. Runtime reloads durable state.
13. Runtime emits a terminal `RuntimeEvent` or returns a terminal `RuntimeResponse`.

### Resume Execution Phase

1. Caller submits a `RuntimeRequest` with `resume_token`.
2. Runtime creates a new `PhaseContext`.
3. Runtime loads durable state and reconstructs `ThreadContext`.
4. Runtime delegates token validation and resume-entry construction to `ResumeService`.
5. `ResumeService` decodes the token into `ResumeTokenPayload`.
6. `ResumeService` validates thread identity, token expiration, and suspend-entry identity against the current thread tail.
7. `ResumeAuthorizationPolicy` evaluates whether the decoded payload may resume the durable `SuspendEntry`.
8. If resume validation or authorization fails, runtime emits an `ERROR` outcome.
9. If resume is allowed, runtime appends a `ResumeEntry` using CAS.
10. Runtime follows the same orchestration flow as a new execution phase.

### Suspend Flow

1. A participating agent or orchestration strategy emits a terminal `suspend` `AgentEvent`.
2. Runtime converts the event into a durable `SuspendEntry`.
3. Runtime appends the `SuspendEntry` using CAS.
4. Runtime reloads durable state.
5. Runtime creates a resume token from the durable suspend entry.
6. Runtime emits a `SUSPEND` outcome containing the resume token.

`SuspendService` is configured as a post-terminal notification/routing collaborator. Runtime invokes it after the suspend entry is durable and the resume token has been created. Failures are best-effort and non-fatal.

### Error Flow

1. A participating agent or orchestration strategy may emit a terminal `error` `AgentEvent`.
2. Runtime converts the event into a durable `ErrorEntry`.
3. Runtime appends the `ErrorEntry` using CAS.
4. Runtime reloads durable state.
5. Runtime emits an `ERROR` outcome.

If orchestration raises an unexpected exception, runtime attempts to append a durable `ErrorEntry` and emits an `ERROR` runtime outcome.

## 7. Participating Components

### FlotillaRuntime

Owns the runtime execution lifecycle. It accepts `RuntimeRequest`, creates `PhaseContext`, loads durable thread state, applies policy checks, appends entries, invokes orchestration, and emits runtime output.

### Runtime I/O

Runtime I/O defines the objects that developers and adapters use at the runtime boundary.

#### RuntimeRequest

`RuntimeRequest` is the canonical input to `FlotillaRuntime`. It identifies the target thread, requesting user, input content, optional resume token, and optional correlation or tracing metadata.

#### RuntimeResponse

`RuntimeResponse` is the synchronous terminal result returned by `run()`. It represents one of three outcomes: `COMPLETE`, `SUSPEND`, or `ERROR`.

#### RuntimeEvent

`RuntimeEvent` is the streaming output yielded by `stream()`. It represents execution start, incremental parts, and terminal outcomes.

#### ResumeToken

`ResumeToken` is the opaque value returned on suspend and supplied on a later `RuntimeRequest` to resume execution. Runtime validates it against durable suspend state before creating a resume phase.

### PhaseContext and PhaseContextService

Provide immutable per-phase metadata. Runtime constructs a new `PhaseContext` for each execution phase.

### ThreadEntryStore

Creates durable thread identities and owns durable thread-log persistence, append-only mutation, store-assigned identity, timestamps, ordering, and CAS behavior.

### Thread Model

Defines durable `ThreadEntry` types and the immutable `ThreadContext` reconstructed from the durable log.

### OrchestrationStrategy

Defines the execution topology for a phase. It coordinates agents or nested strategies and yields canonical `AgentEvent` objects.

### FlotillaAgent

Performs agent reasoning against immutable `ThreadContext` and `PhaseContext`, emitting canonical `AgentEvent` objects.

### AgentEvent

Defines the internal execution event protocol between agents, strategies, and runtime.

### ResumeService

Creates resume tokens from durable suspend entries and validates resume requests before runtime appends a `ResumeEntry`.

### ResumeAuthorizationPolicy

Evaluates whether a decoded resume token payload is authorized to resume a durable suspend entry for the current phase context.

### ExecutionTimeoutPolicy

Determines whether an active phase has expired. Runtime owns timeout enforcement.

### SuspendService

Defines a best-effort post-terminal suspend notification hook. It does not own durable mutation or resume authorization.

### TelemetryService

Receives structured telemetry events emitted by runtime and collaborators. Telemetry is non-authoritative and non-fatal.

## 8. Policies and Rules

### Thread Existence

Runtime requests require an existing thread. Missing threads produce an error outcome.

### Durable Authority

Durable state is authoritative only after `ThreadEntryStore.load()` and `ThreadContext` reconstruction. Runtime MUST reload durable state after successful appends before relying on updated state.

### CAS and Concurrency

All durable appends are conditional against the current thread tail. Concurrent modification failures produce an error outcome and MUST NOT be silently treated as success.

### Terminal Outcome

Each completed execution phase must produce exactly one terminal outcome:

- `AgentOutput`
- `SuspendEntry`
- `ErrorEntry`

### Non-Terminal Events

Non-terminal agent events may be streamed to callers but are not durably persisted.

### Resume Safety

Resume requires:

- A provided resume token.
- A decoded token matching the requested thread.
- A current thread tail that is the referenced `SuspendEntry`.
- A non-expired token.
- Authorization approval from `ResumeAuthorizationPolicy`.

### Timeout Recovery

If a thread has an active phase when a new request arrives, runtime evaluates timeout policy. Expired active phases may be closed by appending an `ErrorEntry`; non-expired active phases reject the new request.

### Telemetry

Telemetry must not alter execution correctness, ordering, durability, or caller-visible outcomes.

## 9. Data Flow

```text
ThreadEntryStore.create_thread()
    -> thread_id
    -> RuntimeRequest
    -> PhaseContext
    -> ThreadEntryStore.load()
    -> ThreadContext
    -> UserInput or ResumeEntry append
    -> ThreadEntryStore.load()
    -> OrchestrationStrategy
    -> AgentEvent stream
    -> RuntimeEvent stream
    -> terminal ThreadEntry append
    -> ThreadEntryStore.load()
    -> terminal RuntimeEvent / RuntimeResponse
```

Durable data flow:

- `RuntimeRequest.content` becomes `UserInput.content` or `ResumeEntry.content`.
- Terminal `AgentEvent.content` becomes `AgentOutput`, `SuspendEntry`, or `ErrorEntry` content.
- `SuspendEntry` becomes the source for resume token creation.

Ephemeral data flow:

- `message_start` and `message_chunk` may become streaming `RuntimeEvent` objects.
- `PhaseContext` exists only for the execution phase.
- Telemetry events are observational and do not become thread state.

## 10. Cross-Cutting Requirements

### Determinism

Runtime lifecycle decisions must derive from durable thread state, immutable phase context, explicit policy decisions, and emitted agent events.

### Immutability

`RuntimeRequest`, `PhaseContext`, `ThreadContext`, `ThreadEntry`, `AgentEvent`, `RuntimeEvent`, and `RuntimeResponse` are treated as immutable values.

### Ordering

Thread entries are append-only and ordered by the store. Event streams must preserve causal ordering.

### Fault Handling

Runtime converts expected validation, resume, concurrency, timeout, and orchestration failures into `ERROR` outcomes.

### Transport Independence

The capability defines runtime behavior independent of HTTP, CLI, messaging, or other transport mechanisms.

## 11. Success Criteria

This capability is successful when:

- Runtime rejects requests for missing threads.
- Runtime appends exactly one phase-initiating entry per accepted request.
- Runtime reloads durable state after successful append operations.
- Runtime streams non-terminal progress without durable mutation.
- Runtime appends exactly one terminal entry per completed phase.
- Runtime returns or emits terminal `COMPLETE`, `SUSPEND`, or `ERROR` outcomes.
- Resume requests are rejected unless they match current durable suspend state and authorization policy.
- Concurrent thread modifications are detected through CAS and surfaced as errors.
- Telemetry failures do not affect execution outcomes.

## 12. Related Specifications

- FlotillaRuntime Specification
- Runtime I/O Specification
- AgentEvent Specification
- FlotillaAgent Specification
- OrchestrationStrategy Specification
- Thread Model Specification
- ThreadEntryStore Specification
- ExecutionTimeoutPolicy Specification
- ResumeAuthorizationPolicy Specification
- SuspendService Specification
- TelemetryService Specification
