# Flotilla

Flotilla is an open-source Python framework for building **production-grade, agent-centric services** with durable execution, explicit runtime contracts, resumable workflows, and structured orchestration.

It is designed to provide the **architectural foundation around agent execution libraries**, making it easier to build AI-enabled services that are testable, operable, and easier to reason about in production.

## Why Flotilla?

Most agent tooling makes it easy to get started, but much harder to build systems that are durable, testable, and operationally clear.

Flotilla is designed for the layer **above raw agent execution**: the application and runtime structure required to run agent-centric workflows as real services.

Flotilla is built around a different philosophy:

- **Durable execution** — workflows are modeled around persisted thread state
- **Suspend / Resume support** — designed for human-in-the-loop and long-running workflows
- **Explicit runtime boundaries** — clear contracts between orchestration, agents, tools, and durable state
- **Framework-agnostic core design** — adapters can integrate with execution libraries without coupling the runtime to them
- **Production-oriented architecture** — intended for real applications, not just demos

Flotilla is especially well-suited for use cases such as:
- approval workflows
- operational exception handling
- support and remediation flows
- structured multi-step AI interactions
- agent systems that need auditability or resumability

---

## What Flotilla Is (and Isn’t)

Flotilla is **not** intended to replace agent execution libraries such as **LangChain**, **LangGraph**, or **Haystack**.

Instead, Flotilla is designed to provide the **application structure and runtime architecture** needed to build production-grade, agent-centric services.

In practical terms:

- **Libraries like LangChain, LangGraph, or Haystack** help execute agent logic, prompts, model interactions, and tool calls
- **Flotilla** provides the surrounding structure for durability, orchestration, suspend/resume workflows, runtime boundaries, application integration, and operational clarity

Flotilla is best thought of as the **service and runtime layer around agent execution**, rather than a direct competitor to model or agent execution frameworks.

This separation is intentional.

The goal is to let developers use the execution libraries they prefer while still building systems with:

- durable workflow state
- explicit execution contracts
- framework-independent runtime structure
- production-oriented service boundaries
- clear separation between orchestration, agents, tools, and infrastructure

---

## Project Status

> **Flotilla is in early development (pre-1.0).**

The architecture is actively evolving, but the project is already focused on a stable set of core ideas:

- runtime orchestration
- durable thread execution
- suspend / resume workflows
- agent and tool contracts
- framework adapters
- application integration

Expect APIs and package structure to evolve before a stable 1.0 release.

---

## Core Concepts

Flotilla is organized around a few core concepts:

### Runtime
The runtime is responsible for executing workflows, consuming agent events, and coordinating durable state transitions.

### Thread
A thread is the durable execution log for a workflow or conversation.

### Agent
An agent is a reasoning unit that emits structured execution events.

### Tool
A tool is a callable capability exposed to an agent.

### Suspend / Resume
Workflows can intentionally suspend and later resume, enabling human-in-the-loop and long-running processes.

### Adapter
Adapters integrate Flotilla with external libraries and application frameworks.

---

## Current Architecture Direction

At a high level, Flotilla is being designed with a strong separation of concerns:

- **Configuration loading** resolves configuration inputs into a fully resolved configuration model
- **Compilation** turns configuration into a deterministic dependency graph
- **Container wiring** builds the runtime object graph
- **Runtime orchestration** manages execution and durable state transitions
- **Agents** emit structured execution events
- **Thread storage** provides append-only durable workflow state

This separation is intentional: Flotilla aims to make agentic systems easier to reason about, test, and operate.

---

## Getting Started

> Quickstart instructions will continue to evolve as the project stabilizes.

### Requirements

- Python 3.10+
- [Poetry](https://python-poetry.org/)

### Clone the repository

```bash
git clone https://github.com/flotilla-dev/flotilla.git
cd flotilla
```

### Run tests
```bash
poetry run pytest
```

## Repository Structure

This structure may evolve during early development.

packages/
  flotilla_core/        # Core runtime, contracts, orchestration, and container
  flotilla_langchain/   # LangChain adapter integration
  flotilla_fastapi/     # FastAPI application integration
  flotilla_sql/         # SQL-backed persistence implementations
  flotilla_testing/     # Shared testing contracts and fixtures
example_app/            # Example application(s)
docs/                   # Design notes, specs, and architecture docs

## Design Principles

Flotilla is being built around a few core design principles:

- Explicit over implicit
- Durability over convenience
- Clear contracts over framework magic
- Composable architecture over monolith abstractions
- Developer ergonomics without hiding system behavior
- Roadmap (Early)

Near-term areas of focus include:

- core runtime stabilization
- suspend / resume workflow examples
- SQL-backed durable thread storage
- FastAPI integration
- improved developer onboarding
- public documentation and examples

## Contributing

Contributions, ideas, and feedback are welcome.

Please read CONTRIBUTING.md before opening a pull request.

## Security

If you believe you’ve found a security issue, please do not open a public GitHub issue.

## License

Flotilla is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) 