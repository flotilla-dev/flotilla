# `CONTRIBUTING.md`

```md
# Contributing to Flotilla

Thanks for your interest in contributing to Flotilla.

Flotilla is an early-stage open-source framework focused on durable, production-oriented agent orchestration. Contributions are welcome, especially those that improve correctness, clarity, developer experience, and long-term maintainability.

## Ways to Contribute

Contributions can include:

- bug fixes
- tests
- documentation improvements
- examples
- design clarifications
- new integrations or adapters
- implementation improvements aligned with project direction

If you’re unsure whether something is a good fit, opening an issue or discussion first is encouraged.

---

## Before You Start

Because Flotilla is still evolving, it’s helpful to align on larger changes before investing significant implementation work.

Please consider opening an issue or discussion first if your proposed change:

- introduces a new architectural pattern
- changes public APIs or core contracts
- adds a new package or integration
- changes runtime or persistence behavior
- modifies core configuration or compiler semantics

Small fixes and improvements usually do not need prior discussion.

---

## Development Setup

### Requirements

- Python 3.10+
- [Poetry](https://python-poetry.org/)

### Clone the repository

```bash
git clone https://github.com/YOUR-ORG/flotilla.git
cd flotilla
```

### Install dependencies
```bash
poetry install
```

### Run tests
```bash
poetry run pytest
```

### Development Expectations

Flotilla is intentionally being built with a strong emphasis on explicit contracts and correctness.

When contributing, please aim to keep changes:

- well-scoped
- well-tested
- consistent with the project’s design philosophy
- easy to review

In general, contributions should:
- include tests for behavior changes
- update docs when introducing or changing public behavior
- preserve clear boundaries between components
- avoid adding hidden state or implicit behavior
- favor explicit contracts over convenience shortcuts

### Code Style

At a high level, Flotilla favors:

- readable, explicit Python
- small, composable abstractions
- clear naming
- deterministic behavior
- minimal framework magic

A few general guidelines:

- prefer clarity over cleverness
- avoid over-generalizing too early
- keep responsibilities sharply separated
- favor explicit configuration and contracts
- avoid introducing hidden side effects

### Tests

Tests are an important part of the project and are expected for meaningful behavior changes.

Please add or update tests when your contribution affects:

- runtime behavior
- agent or tool contracts
- thread persistence behavior
- configuration or compiler semantics
- framework adapters
- public APIs

If a change is intentionally breaking or changes expected behavior, tests should make that explicit.

Run the test suite locally before opening a pull request:

```bash
poetry run pytest
```

### Documentation

Documentation is part of the product.

If your change affects behavior, architecture, public APIs, or developer workflows, please update the relevant documentation as part of the same pull request whenever possible.

This may include:

- README updates
- docs/ content
- examples
- inline code comments where appropriate

### Pull Requests

When opening a pull request, please try to include:

- what changed
- why it changed
- how it was tested
- any important tradeoffs or follow-up work

Smaller, focused pull requests are strongly preferred over large mixed changes.

### Design Philosophy

Flotilla is being built around a few core principles:

- Explicit over implicit
- Durability over convenience
- Clear contracts over hidden framework behavior
- Composability over monolithic abstraction
- Operational clarity over demo-oriented shortcuts

Contributions that align with these principles are much more likely to fit the project well.

### Questions / Discussion

If you have questions, ideas, or want to discuss a change before implementing it, feel free to open a discussion or issue.

