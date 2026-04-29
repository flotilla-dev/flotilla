# Flotilla Configuration Overview

## 1. Executive Summary

Flotilla configuration defines a declarative component graph that is compiled
into a validated dependency injection container.

Configuration in Flotilla is treated as code that builds, not data that is
interpreted dynamically at runtime. The build process guarantees that if
startup succeeds:

- the dependency graph is valid
- all component references resolve
- all configuration directives are materialized
- singleton components are constructed
- factory bindings are validated and ready to create parameterized instances
- component lifecycle ownership is known

Configuration is typically authored in YAML, but YAML is not required. Any
source capable of producing a Python `Dict[str, Any]` that conforms to the
Flotilla configuration grammar may be used.

## 2. Configuration Model

A Flotilla configuration describes a component registry specification.

Each definition declares:

- how a component or factory binding is constructed
- the arguments used to construct it
- the dependencies between bindings
- optional lifecycle participation through component protocols

Dependencies are expressed declaratively through directives such as `$ref`.
Factory references may include `$params` to provide call-site parameters.

The configuration graph is compiled into a runtime container through a
deterministic build process. The grammar and directive semantics are formally
defined in the Flotilla Configuration Rules specification.

## 3. Configuration Sources

Flotilla does not require configuration to originate from a specific file
format. Configuration is supplied through objects implementing the
`ConfigurationSource` interface.

```python
class ConfigurationSource(Protocol):
    def load(self) -> Dict[str, Any] | Awaitable[Dict[str, Any]]: ...
```

Each source returns a configuration fragment represented as a Python dictionary.

Examples of configuration sources include:

- YAML configuration files
- Python functions returning configuration dictionaries
- Python objects exposing selected configuration methods
- environment-derived configuration
- remote configuration services
- dynamically generated configuration

Flotilla includes built-in implementations such as:

- `YamlConfigurationSource`
- `DictConfigurationSource`

`YamlConfigurationSource` loads one explicit YAML file path. To layer multiple
YAML files, pass multiple sources to `ConfigLoader` in the desired order. Later
files override earlier files.

Python configuration sources are the preferred way to mix programmatic
configuration with YAML. A Python source may return a whole configuration tree
or one fragment among many. Multiple methods may be composed by a source in a
known order and merged with the same source-ordering semantics as YAML.

A Python configuration callable looks similar to a provider because both are
plain Python callables. The distinction is the phase and output:

- configuration callables run during loading and return spec dictionaries
- providers run during compilation and return component instances
- factory bindings run during resolution and return new component instances

This lets app developers write simple Python functions for configuration without
turning configuration into object construction.

## 4. Configuration And Container Pipeline

```text
Configuration Sources
  -> ConfigLoader
     - merge sources
     - resolve $secret
  -> FlotillaSettings
  -> ComponentCompiler
     - build unified registry
     - validate references and cycles
     - install singleton and factory bindings
  -> FlotillaContainer
     - async get()
     - async startup()
     - async shutdown()
  -> Runtime Execution
```

Each phase performs a specific transformation and guarantees invariants required
by the next phase.

## 5. Phase 1: Configuration Loading

Component: `ConfigLoader`

`ConfigLoader` constructs a deterministic configuration dictionary from all
configured sources.

Responsibilities include:

- loading configuration fragments from `ConfigurationSource` objects
- merging fragments into a single configuration graph
- resolving `$secret` directives

After this phase completes, no configuration-loader directives remain. The
resulting structure is wrapped in `FlotillaSettings` and passed to the compiler.

## 5.1 Source Merging

Configuration fragments returned by each `ConfigurationSource` are merged into a
single configuration graph.

Merge semantics:

- sources are applied in order
- later sources override earlier sources
- mappings are deep-merged
- scalar values and lists replace earlier values

This allows configuration layering such as:

- base YAML configuration
- environment-specific YAML overrides
- Python-generated component definitions
- test or runtime-specific overrides

## 5.2 Secret Resolution

Secret values are resolved using `SecretResolver` implementations. Resolvers map
secret identifiers to actual values.

Typical implementations may retrieve secrets from:

- environment variables
- secret managers
- encrypted configuration stores

Secret resolution occurs during configuration loading so that secret values
never appear in unresolved form during compilation.

## 6. Phase 2: Component Compilation

Component: `ComponentCompiler`

`ComponentCompiler` transforms configuration definitions and Python-registered
definitions into a unified build registry.

The compiler:

1. Discovers singleton component definitions.
2. Discovers factory binding definitions.
3. Includes pre-build Python registrations.
4. Validates dependency references across the full registry.
5. Detects cycles.
6. Instantiates singleton bindings in dependency order.
7. Installs factory bindings without eagerly creating produced instances.

The result is a frozen `FlotillaContainer` containing validated bindings.

## 7. Component And Factory Construction

Singleton components are defined with `$provider` or `$class`.

```yaml
database:
  $provider: postgres.connection
  host: localhost
```

```yaml
cache:
  $class: redis.Redis
  host: localhost
```

Factory bindings are defined with `$factory`.

```yaml
llm_factory:
  $factory: llm.openai
  model: gpt-4o-mini
```

A factory binding creates a new instance whenever it is resolved.

```python
llm = await container.get("llm_factory", temperature=0.1)
```

## 8. Dependency Graph

Dependencies between bindings are declared with `$ref`.

```yaml
service:
  $provider: services.user
  database:
    $ref: database
```

Factory references may include `$params`.

```yaml
agent:
  $provider: agents.weather
  llm:
    $ref: llm_factory
    $params:
      temperature: 0.1
      max_tokens: 500
```

`$params` is valid only when the referenced binding is a factory binding.
Singleton bindings reject parameterized references during compilation.

## 9. Component Identity

Each binding registered in the container has a unique identity used for `$ref`
resolution.

If a definition contains `$name`, that value becomes the binding identity. If
`$name` is not present, the compiler derives the identity from the configuration
path of the definition.

```yaml
services:
  user_service:
    $provider: services.user
```

Produces the identity:

```text
services.user_service
```

The same identity space is shared by YAML definitions, Python configuration
sources, and pre-build Python registrations.

## 10. Container Runtime Surface

`FlotillaContainer.get()` is async for all bindings.

```python
service = await container.get("service")
llm = await container.get("llm_factory", temperature=0.1)
```

Singleton bindings return their constructed instance. Factory bindings create a
new instance on each call and accept call-site keyword arguments.

The container also owns component lifecycle:

```python
await container.startup(timeout=30)
await container.shutdown(timeout=30)
```

Components opt into lifecycle with `startup()` and/or `shutdown()` methods.
Lifecycle methods may be sync or async. Awaitable lifecycle calls are bounded by
the container-provided timeout.

Startup runs in dependency order. Shutdown runs in reverse dependency order and
is best-effort. `FactoryBinding` tracks instances it creates and relays
lifecycle calls to those instances.

## 11. Determinism Guarantee

Flotilla's build model provides a strong guarantee:

> If the application starts successfully, the component registry is valid.

This ensures:

- no missing dependencies
- no circular references
- no unresolved directives
- no invalid factory parameterization
- deterministic singleton instantiation
- known lifecycle ownership

Runtime execution interacts with the built container and concrete bindings, not
raw configuration.

## 12. Relationship To Configuration Rules

This document describes the architecture and lifecycle of configuration in
Flotilla. The formal grammar, directive definitions, and structural validation
rules are defined in the Flotilla Configuration Rules specification.
