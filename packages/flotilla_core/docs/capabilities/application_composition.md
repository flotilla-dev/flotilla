# Application Composition Capability Specification (v0.1-draft)

## 1. Executive Summary

Application Composition is how Flotilla turns configuration and Python
registrations into a built, started dependency injection container.

The capability allows app developers to combine:

- YAML configuration files
- Python configuration functions
- Python configuration objects
- pre-build component definitions
- pre-build factory definitions
- registered providers

The result is a `FlotillaContainer` with validated singleton bindings, factory
bindings, and lifecycle ownership.

## 2. Goals

Application Composition must let developers:

- mix YAML and Python-generated component definitions
- define singleton components
- define factory bindings that create parameterized instances
- reference bindings consistently through `$ref`
- pass factory call-site arguments through `$params`
- validate references and cycles before runtime execution
- start and shut down lifecycle-aware components through the container

## 3. Scope

This capability includes:

- loading configuration sources
- merging configuration fragments
- resolving secrets
- building a unified component registry
- compiling singleton and factory bindings
- resolving components through async `container.get()`
- coordinating async container `startup()` and `shutdown()`

This capability does not include:

- agent execution
- thread persistence
- external transport protocols
- business-domain authorization
- runtime orchestration logic

## 4. Configuration Sources

Configuration enters through `ConfigurationSource` implementations.

```python
class ConfigurationSource(Protocol):
    def load(self) -> Dict[str, Any] | Awaitable[Dict[str, Any]]: ...
```

Sources are applied in order. Later sources override earlier sources. Mappings
are deep-merged. Scalars and lists replace earlier values.

Python configuration sources may wrap:

- one configuration function
- an ordered list of configuration functions
- a selected list of methods from a configuration object

Autodiscovery may be added later as a convenience, but explicit ordering is the
canonical behavior.

Python configuration functions are deliberately plain callables. They return
configuration dictionaries that describe component and factory definitions. They
do not construct runtime objects.

Providers are also callables, but they run later and have a different role:

- configuration function: returns a spec dictionary
- provider: returns a runtime object
- factory binding: returns a new runtime object each time it is resolved

This keeps programmatic configuration ergonomic without making app developers
inherit framework classes for ordinary configuration composition.

## 5. Build Workflow

1. `ConfigLoader` loads all sources.
2. `ConfigLoader` merges the source fragments.
3. `ConfigLoader` resolves `$secret`.
4. `FlotillaContainer` is created with `FlotillaSettings`.
5. Providers are registered.
6. Python component and factory definitions are registered.
7. `container.build()` invokes `ComponentCompiler`.
8. `ComponentCompiler` builds one unified registry.
9. `ComponentCompiler` validates names, references, parameters, and cycles.
10. `ComponentCompiler` installs singleton and factory bindings.
11. The container registry is frozen.

After build succeeds, application code may call:

```python
await container.startup(timeout=30)
component = await container.get("component")
await container.shutdown(timeout=30)
```

## 6. Registry Model

The compiler registry is the single source of truth during build.

The registry may contain definitions from YAML and Python. A binding reference is
valid if it resolves against the full registry, not only the YAML fragment.

Allowed registry entries:

- singleton component definition
- factory binding definition
- explicit instance binding for framework integration

Application developers should register definitions before build. The compiler
installs resolved bindings into the container.

## 7. Binding Types

### Singleton Binding

A singleton binding owns exactly one component instance.

Singleton instances are created during build. They may participate in container
lifecycle if they implement `startup()` or `shutdown()`.

Singleton bindings reject call-site kwargs.

### Factory Binding

A factory binding owns a callable and default keyword arguments.

Resolving the binding creates a new instance.

```python
instance = await container.get("factory_name", **kwargs)
```

Factory bindings:

- merge default kwargs with call-site kwargs
- let call-site kwargs override defaults
- track generated instances
- start generated instances when appropriate
- shut down generated instances in reverse creation order

## 8. Reference Semantics

`$ref` resolves a binding by identity.

```yaml
dependency:
  $ref: service
```

`$ref` with `$params` resolves a factory binding with call-site arguments.

```yaml
dependency:
  $ref: llm_factory
  $params:
    temperature: 0.1
```

Rules:

- `$ref` may target singleton or factory bindings.
- `$params` may only target factory bindings.
- `$params` against a singleton binding fails build.
- `$params` values are materialized before factory invocation.

## 9. Lifecycle

Components opt into lifecycle by exposing either method:

```python
def startup() -> None | Awaitable[None]: ...
def shutdown() -> None | Awaitable[None]: ...
```

The container exposes:

```python
await container.startup(timeout=30)
await container.shutdown(timeout=30)
```

Startup rules:

- startup requires a built container
- startup runs in dependency order
- awaitable startup methods are bounded by timeout
- startup failure triggers shutdown of already-started bindings

Shutdown rules:

- shutdown runs in reverse dependency order
- shutdown is best-effort
- awaitable shutdown methods are bounded by timeout
- shutdown may be called after failed or partial startup
- repeated shutdown calls are no-ops

Synchronous lifecycle methods must not block. Timeout enforcement applies to
awaitable lifecycle work.

## 10. State Transitions

The container lifecycle uses explicit states:

```text
CREATED -> BUILT -> STARTING -> STARTED -> SHUTTING_DOWN -> SHUTDOWN
```

Invalid transitions fail deterministically:

- startup before build is invalid
- build after build is invalid
- mutation after build is invalid
- get after shutdown is invalid

Shutdown remains valid after partial startup failure.

## 11. Error Handling

Build errors fail before application startup. Examples:

- duplicate binding names
- missing providers
- missing references
- dependency cycles
- `$params` used with a singleton binding
- invalid directive structure

Startup errors include the binding name and phase. If startup fails, the
container attempts to shut down already-started bindings.

Shutdown errors are collected while shutdown continues across remaining
bindings. After best-effort shutdown completes, the container reports aggregated
failures.

## 12. Success Criteria

This capability is successful when:

- YAML and Python definitions can participate in the same registry.
- YAML definitions can reference Python definitions.
- Python definitions can reference YAML definitions.
- singleton components are built in dependency order.
- factory bindings create parameterized instances through async `get()`.
- `$params` is accepted only for factory references.
- lifecycle-aware components are started and shut down by the container.
- factory-created instances are lifecycle-managed by their `FactoryBinding`.
- invalid wiring fails before runtime execution.

## 13. Related Specifications

- Configuration Architecture
- Configuration Overview
- Configuration Rules
- Agent Orchestration
