# Flotilla Configuration Architecture

## What Is Flotilla Configuration?

Flotilla is a declarative component registry system. Configuration from YAML,
Python, or other sources is loaded, validated, compiled into container bindings,
and then started as part of application lifecycle.

The core idea remains:

- configuration errors are caught during build/startup
- component references are validated before runtime execution
- singleton components are instantiated deterministically
- factory bindings are validated and can create parameterized instances
- component lifecycle is coordinated by the container

## Pipeline

```text
Configuration Sources
        |
        v
   ConfigLoader
   - merge sources
   - resolve $secret
        |
        v
  FlotillaSettings
        |
        v
  ComponentCompiler
   - collect YAML definitions
   - collect Python definitions
   - validate full registry
   - install bindings
        |
        v
  FlotillaContainer
   - async get()
   - async startup()
   - async shutdown()
        |
        v
 Runtime Execution
```

Each phase has strict responsibilities and provides specific guarantees to the
next phase.

## Phase 1: Configuration Loading

Component: `ConfigLoader`

Mission: transform configuration sources into a single deterministic
configuration tree.

The loader handles:

- multi-source merging
- secret resolution
- async or sync source loading

After `ConfigLoader` runs:

- source ordering has been applied
- no `$secret` directives remain
- the configuration dictionary is wrapped in `FlotillaSettings`

The loader does not resolve component references, create components, or perform
factory semantics.

## Phase 2: Registry Compilation

Component: `ComponentCompiler`

Mission: build a unified registry from declarative configuration and Python
registrations, then install validated container bindings.

The registry can contain:

- singleton component definitions from YAML
- factory definitions from YAML
- singleton component definitions from Python configuration sources
- factory definitions from Python configuration sources
- pre-build Python component definitions
- pre-build Python factory definitions
- explicit instance bindings for framework integration

The compiler validates:

- duplicate names
- missing references
- dependency cycles
- provider availability
- factory parameterization
- invalid singleton parameterization
- structural grammar violations

The compiler installs:

- `SingletonBinding` for `$provider` and `$class` definitions
- `FactoryBinding` for `$factory` definitions

## Singleton Bindings

Singleton definitions are instantiated during build in dependency order.

```yaml
store:
  $provider: stores.memory

runtime:
  $provider: runtime.default
  store:
    $ref: store
```

The compiler materializes `$ref`, `$list`, and `$map` values before invoking the
provider.

## Factory Bindings

Factory definitions are installed during build but do not eagerly create their
produced instances.

```yaml
llm_factory:
  $factory: llm.openai
  model: gpt-4o-mini
```

Resolving a factory binding creates a new instance.

```python
llm = await container.get("llm_factory", temperature=0.1)
```

Factories may also be referenced from configuration.

```yaml
agent:
  $provider: agents.weather
  llm:
    $ref: llm_factory
    $params:
      temperature: 0.1
```

`$params` is only valid for factory references. Passing parameters to a
singleton reference is a build error.

## Python And YAML Composition

Python and YAML definitions participate in one registry. This allows:

- YAML components to depend on Python-defined components
- Python-defined components to depend on YAML components
- YAML and Python factories to be consumed through the same `$ref` semantics

Application developers should register component definitions, not finished
components. Installing resolved component bindings is the compiler's job.

Python configuration sources are the preferred way to contribute programmatic
configuration:

```python
def configure_runtime():
    return {
        "runtime": {
            "$provider": "runtime.default",
        }
    }
```

Multiple Python configuration methods may be composed by a source in a known
order and merged like any other configuration source.

Although Python configuration functions and providers are both callables, they
belong to different phases. Configuration functions return dictionaries that
describe definitions. Providers return actual runtime objects. Factory bindings
wrap providers or factory callables and create new runtime objects when
resolved.

## Container Lifecycle

The container has an explicit async lifecycle.

```python
await container.build()
await container.startup(timeout=30)
component = await container.get("component")
await container.shutdown(timeout=30)
```

Components opt into lifecycle by implementing either method:

```python
def startup() -> None | Awaitable[None]: ...
def shutdown() -> None | Awaitable[None]: ...
```

Startup behavior:

- runs after build
- runs in dependency order
- applies timeout to awaitable lifecycle calls
- if startup fails, already-started bindings are shut down

Shutdown behavior:

- runs in reverse dependency order
- continues best-effort across failures
- applies timeout to awaitable lifecycle calls
- is safe to call after partial startup failure

`FactoryBinding` tracks every instance it creates. If the container has already
started, a factory-created instance is started before it is returned. During
shutdown, factory-created instances are shut down in reverse creation order.

## Runtime Contract

After successful startup:

- singleton components are constructed
- factory bindings are ready for async resolution
- all known dependency edges are valid
- lifecycle ownership is known
- raw configuration directives do not reach runtime collaborators

The runtime may resolve factory bindings to create new instances, but those
instances are still owned by the binding that created them.

## Design Philosophy

### Explicit Over Implicit

Every binding must be declared. Every reference must resolve. Every parameterized
reference must target a factory.

### Build-Time Validation

Flotilla should fail before application execution when the component registry is
invalid. Runtime code should not discover missing providers or invalid
references by accident.

### Mixed Source Composition

YAML is a convenient human-authored format, not the only source of truth.
Python-generated configuration and pre-build Python registrations are first
class contributors to the same registry.

### Lifecycle As Ownership

The binding that owns an instance is responsible for starting it and shutting it
down. Singleton bindings own singleton instances. Factory bindings own the
instances they create.

## When To Use Flotilla

Flotilla is useful when an application has:

- mixed YAML and Python composition needs
- multiple components with explicit dependencies
- resources requiring startup and shutdown coordination
- factories that create parameterized runtime objects
- a need for build-time validation of wiring

It may be unnecessary for small applications with only a few hand-wired objects.
