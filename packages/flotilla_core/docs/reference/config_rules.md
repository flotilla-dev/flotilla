# Flotilla Configuration Rules

This document defines the configuration grammar and container build rules for
Flotilla.

Flotilla configuration is a declarative component graph specification language.
It may be authored in YAML, Python, or any other source that produces the same
configuration dictionary. The configuration is compiled into a validated
component registry and then into container bindings.

## Core Principles

- Explicit is required.
- Implicit is forbidden.
- Structure is enforced.
- Configuration sources may be mixed.
- Component wiring errors fail during build, not runtime execution.

## Configuration Sources

Configuration fragments are provided by objects implementing the
`ConfigurationSource` protocol.

```python
class ConfigurationSource(Protocol):
    def load(self) -> Dict[str, Any] | Awaitable[Dict[str, Any]]: ...
```

Examples include:

- YAML files
- Python functions returning configuration fragments
- Python objects exposing selected configuration methods
- environment-derived configuration
- remote configuration services
- test fixtures

`ConfigLoader` loads all sources and merges them into a single configuration
tree.

Merge semantics:

- sources are applied in order
- later sources override earlier sources
- mappings are deep-merged
- scalar values and lists replace earlier values

## ConfigLoader Phase

`ConfigLoader` is responsible for source-level concerns:

- loading configuration fragments
- merging fragments into one deterministic tree
- resolving `$secret` directives

After `ConfigLoader.load()`:

- no `$secret` directives remain
- the output is wrapped in `FlotillaSettings`
- the result is ready for `ComponentCompiler`

`ConfigLoader` does not perform component construction and does not own
component reuse semantics.

## Component Compiler Phase

`ComponentCompiler` owns the build registry. The registry is the union of:

- component specs discovered from configuration sources
- component specs registered from Python before build
- factory specs discovered from configuration sources
- factory specs registered from Python before build
- explicit instance bindings registered as framework escape hatches

Application developers should register component definitions or factory
definitions, not finished components. Installing resolved component bindings is
an internal compiler/container operation.

The compiler:

1. Discovers component and factory definitions.
2. Merges them with pre-build Python registrations.
3. Validates names, references, parameters, and dependency cycles.
4. Instantiates singleton component bindings in dependency order.
5. Installs factory bindings without eagerly creating produced instances.
6. Freezes the container registry.

## Component Identity

Each binding registered in the container has a unique identity used for `$ref`
resolution.

By default, the compiler derives the component name from the configuration path
of the definition.

```yaml
services:
  user_service:
    $provider: services.user
```

Default component name:

```text
services.user_service
```

If `$name` is provided, it overrides the path-derived identity.

```yaml
agent:
  $provider: agents.weather
  $name: weather_agent
```

Rules:

- names must be unique across YAML and Python registrations
- duplicate names fail compilation
- `$ref` resolution uses the final component identity

## Directives

### `$secret`

Purpose: resolve a secure scalar value from a `SecretResolver`.

Resolution phase: `ConfigLoader`

Syntax:

```yaml
api_key:
  $secret: OPENAI_API_KEY
```

Rules:

- MUST be a mapping node
- MUST contain only `$secret`
- value MUST be a string
- may appear anywhere a value is allowed
- unresolved secrets fail loading
- no `$secret` may exist after `ConfigLoader.load()`

### `$provider`

Purpose: define a singleton component constructed by a registered provider.

Resolution phase: `ComponentCompiler`

Syntax:

```yaml
component:
  $provider: provider.identifier
  arg1: value
  arg2: value
```

Rules:

- MUST be a mapping node
- MUST contain `$provider`
- value MUST be a string
- MUST NOT appear with `$class` or `$factory`
- MAY contain `$name`
- other keys are constructor keyword arguments
- argument values must conform to the Flotilla grammar
- produces a singleton binding

### `$class`

Purpose: define a singleton component constructed through reflection.

Resolution phase: `ComponentCompiler`

Syntax:

```yaml
component:
  $class: package.module.ClassName
  arg1: value
```

Rules:

- MUST be a mapping node
- MUST contain `$class`
- value MUST be a string
- MUST NOT appear with `$provider` or `$factory`
- MAY contain `$name`
- other keys are constructor keyword arguments
- argument values must conform to the Flotilla grammar
- produces a singleton binding

### `$factory`

Purpose: define a factory binding that creates a new instance each time it is
resolved.

Resolution phase: `ComponentCompiler`

Syntax:

```yaml
llm_factory:
  $factory: llm.openai
  model: gpt-4o-mini
```

Rules:

- MUST be a mapping node
- MUST contain `$factory`
- value MUST be a registered provider identifier or factory identifier
- MUST NOT appear with `$provider` or `$class`
- MAY contain `$name`
- other keys are default keyword arguments for the factory
- produces a `FactoryBinding`
- the binding creates instances through `resolve(**kwargs)`
- call-site kwargs override factory defaults
- generated instances are owned by the factory binding for lifecycle purposes

### `$name`

Purpose: override the default component identity.

Resolution phase: `ComponentCompiler`

Syntax:

```yaml
component:
  $provider: example.provider
  $name: custom_component_name
```

Rules:

- optional on `$provider`, `$class`, and `$factory` definitions
- value MUST be a string
- final names must be unique

### `$ref`

Purpose: resolve a container binding by identity.

Resolution phase: `ComponentCompiler`

Syntax:

```yaml
dependency:
  $ref: component_name
```

Parameterized factory syntax:

```yaml
dependency:
  $ref: llm_factory
  $params:
    temperature: 0.1
    max_tokens: 500
```

Rules:

- MUST be a mapping node
- MUST contain `$ref`
- `$ref` value MUST be a string
- MAY contain `$params`
- no other keys are allowed
- scalar form is invalid
- references may target singleton or factory bindings
- `$params` is valid only when the target is a factory binding
- singleton binding plus `$params` fails compilation
- `$params` MUST be a mapping
- `$params` values must conform to the Flotilla grammar
- references must resolve against the full build registry, including YAML and Python registrations
- no `$ref` may reach provider or factory invocation

### `$params`

Purpose: provide call-site keyword arguments when resolving a factory binding.

Resolution phase: `ComponentCompiler`

Rules:

- only valid as a sibling of `$ref`
- MUST be a mapping
- only valid when `$ref` targets a factory binding
- values are materialized before factory invocation
- call-site values override factory defaults

### `$list`

Purpose: declare an ordered collection of values.

Resolution phase: `ComponentCompiler`

Syntax:

```yaml
items:
  $list:
    - value
    - $ref: component_name
```

Rules:

- MUST be a mapping node
- MUST contain only `$list`
- value MUST be a YAML list
- raw lists are invalid
- elements may be scalars, `$ref`, `$list`, `$map`, or embedded definitions

### `$map`

Purpose: declare a mapping of values.

Resolution phase: `ComponentCompiler`

Syntax:

```yaml
mapping:
  $map:
    primary:
      $ref: component_name
```

Rules:

- MUST be a mapping node
- MUST contain only `$map`
- value MUST be a YAML mapping
- raw arbitrary dicts are invalid
- values may be scalars, `$ref`, `$list`, `$map`, or embedded definitions

## Embedded Definitions

Component and factory definitions may appear anywhere a value is allowed:

- top-level entries
- constructor arguments
- `$list` items
- `$map` values

Embedded singleton definitions produce singleton bindings with path-derived
names. Embedded factory definitions produce factory bindings with path-derived
names.

## Allowed Scalars

Allowed scalar values:

- string values that do not begin with `$`
- int
- float
- bool
- null

Disallowed scalar directive forms:

- `$provider something`
- `$factory something`
- `$name something`
- `$ref something`
- `$list something`
- `$map something`
- `$params something`
- `$secret something`

All directives must use mapping form.

## Canonical Structural Rule

A mapping node is valid if and only if it satisfies exactly one of:

1. Contains exactly one definition directive: `$provider`, `$class`, or `$factory`.
2. Contains `$ref`, optionally with `$params`.
3. Contains exactly one collection directive: `$list` or `$map`.
4. Contains exactly one configuration directive: `$secret`.

Any other mapping node is invalid unless it is the root configuration mapping or
a source-level grouping mapping that contains nested valid nodes.

## Container Binding Resolution

`FlotillaContainer.get()` is async for all bindings.

```python
component = await container.get("component_name")
instance = await container.get("llm_factory", temperature=0.1)
```

Rules:

- `get(name)` resolves the named binding
- singleton bindings return their singleton instance
- singleton bindings reject call-site kwargs
- factory bindings create a new instance on each call
- factory bindings accept call-site kwargs
- call-site kwargs override factory default kwargs
- missing bindings fail with a configuration error

## Component Lifecycle

Components may opt into lifecycle management by implementing either protocol.

```python
class Startup(Protocol):
    def startup(self) -> None | Awaitable[None]: ...

class Shutdown(Protocol):
    def shutdown(self) -> None | Awaitable[None]: ...
```

The container exposes async lifecycle methods:

```python
await container.startup(timeout=30)
await container.shutdown(timeout=30)
```

Lifecycle rules:

- `startup()` may only run after build succeeds
- startup runs in dependency order
- shutdown runs in reverse dependency order
- shutdown is best-effort and should continue across component failures
- lifecycle calls may be synchronous or awaitable
- awaitable lifecycle calls are bounded by the provided timeout
- synchronous lifecycle calls must not block
- startup failure triggers shutdown of already-started bindings
- generated factory instances are tracked by their `FactoryBinding`
- if a factory creates an instance after container startup, that instance is started before it is returned
- factory instances shut down in reverse creation order

## Phase Ownership Summary

| Token | Meaning | Resolved by | May reach runtime |
|-------|---------|-------------|-------------------|
| `$secret` | Secure scalar value | ConfigLoader | No |
| `$provider` | Singleton component provider | ComponentCompiler | No |
| `$class` | Singleton reflection component | ComponentCompiler | No |
| `$factory` | Factory binding provider | ComponentCompiler | No |
| `$name` | Binding identity override | ComponentCompiler | No |
| `$ref` | Binding reference | ComponentCompiler | No |
| `$params` | Factory call-site parameters | ComponentCompiler | No |
| `$list` | Component/value collection | ComponentCompiler | No |
| `$map` | Component/value mapping | ComponentCompiler | No |

## Global Invariants

After `ConfigLoader`:

- no `$secret`
- source ordering is fully applied

After `ComponentCompiler`:

- no `$provider`
- no `$class`
- no `$factory`
- no `$ref`
- no `$params`
- no raw lists
- no raw arbitrary dicts
- container contains validated bindings

If build succeeds:

- the graph is valid
- all dependencies are resolvable
- lifecycle ownership is known
- runtime execution is free of configuration indirection
