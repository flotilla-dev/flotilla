# Flotilla Core Documentation

This directory is organized by level of abstraction.

Start with capabilities when you want to understand how Flotilla works as a workflow. Use component specs when you need precise behavioral contracts for a specific unit. Use reference docs for supporting architecture, configuration, and scenarios.

## Capabilities

Capability specs describe end-to-end behavior across multiple components.

- [Application Composition](capabilities/application_composition.md)
- [Agent Orchestration](capabilities/agent_orchestration.md)

## Components

Component specs describe exact contracts, local responsibilities, data models, and behavioral rules.

### Runtime

- [FlotillaRuntime](components/runtime/flotilla_runtime.md)
- [Runtime I/O](components/runtime/runtime_io.md)
- [OrchestrationStrategy](components/runtime/orchestration_strategy.md)

### Agents

- [FlotillaAgent](components/agents/flotilla_agent.md)
- [AgentEvent](components/agents/agent_event.md)

### Thread

- [Thread Model](components/thread/thread_model.md)
- [ThreadEntryStore](components/thread/thread_entry_store.md)

### Policies

- [ExecutionTimeoutPolicy](components/policies/execution_timeout_policy.md)
- [ResumeAuthorizationPolicy](components/policies/resume_authorization_policy.md)

### Services

- [SuspendService](components/services/suspend_service.md)
- [TelemetryService](components/services/telemetry_service.md)

### Tools

- [FlotillaTool](components/tools/flotilla_tool.md)

### Content

- [ContentPart](components/content/content_part.md)

## Reference

Reference docs provide supporting concepts, configuration rules, and canonical scenarios.

- [Configuration Architecture](reference/architecture_config.md)
- [Configuration Overview](reference/config_overview.md)
- [Configuration Rules](reference/config_rules.md)
- [Canonical Test Scenarios](reference/test_scenarios.md)
