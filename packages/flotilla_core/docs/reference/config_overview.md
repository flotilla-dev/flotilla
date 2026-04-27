# Flotilla Configuration Overview

## 1. Executive Summary

Flotilla configuration defines a **declarative component graph** that is compiled into a fully instantiated dependency injection container before application execution.

Configuration in Flotilla is treated as **code that compiles**, not data that is interpreted dynamically at runtime.

The configuration system guarantees that if compilation succeeds:

-   the dependency graph is valid
-   all component references resolve
-   all configuration directives are fully materialized
-   runtime execution contains no configuration indirection
    

Configuration is typically authored in **YAML**, but YAML is **not required**.  
Any source capable of producing a Python `Dict[str, Any]` that conforms to the Flotilla configuration grammar may be used.

----------

# 2. Configuration Model

A Flotilla configuration describes a **component graph specification**.

Each component definition declares:

-   how the component is constructed
-   the arguments used to construct it
-   the dependencies between components
    
Dependencies are expressed declaratively through configuration directives such as `$ref`.

The configuration graph is compiled into a runtime object graph through a deterministic two-phase compilation process.

The grammar and directive semantics used in configuration are formally defined in the **Flotilla Configuration Rules** specification.

This document focuses on **how configuration flows through the system**, not the detailed syntax rules.

----------

# 3. Configuration Sources

Flotilla does not require configuration to originate from a specific file format.

Instead, configuration is supplied through objects implementing the `ConfigurationSource` interface.
```python
class  ConfigurationSource(Protocol):  
  def  load(self) -> Dict[str, Any] | Awaitable[Dict[str, Any]]
```
Each source returns a configuration fragment represented as a Python dictionary.

Examples of configuration sources include:

-   YAML configuration files
-   Python dictionaries
-   environment-derived configuration
-   remote configuration services
-   dynamically generated configuration
    
Flotilla includes built-in implementations such as:

-   `YamlConfigurationSource`
-   `DictConfigurationSource`

`YamlConfigurationSource` loads one explicit YAML file path. To layer multiple
YAML files, pass multiple sources to `ConfigLoader` in the desired order. Later
files override earlier files, so a developer can load `application.yml` followed
by `dev-override.yml` and only redefine the component entries that should
change.

YAML is the **recommended human-authored format**, but the runtime configuration graph is always represented internally as a Python dictionary.

----------

# 4. Configuration Compilation Pipeline

Flotilla configuration is compiled in two phases.
```
Configuration Sources  
 ↓  
 ConfigLoader  
 (Phase 1: Resolve configuration directives)  
 ↓  
Resolved Configuration Graph  
 ↓  
 ComponentCompiler  
 (Phase 2: Build component graph)  
 ↓  
Dependency Injection Container  
 ↓  
Runtime Execution
```

Each phase performs a specific transformation and guarantees invariants required by the next phase.

----------

# 5. Phase 1: Configuration Resolution

**Component:** `ConfigLoader`

The `ConfigLoader` constructs a fully resolved configuration graph from all configured sources.

Responsibilities include:

-   loading configuration fragments from `ConfigurationSource` object
-   merging fragments into a single configuration graph
-   resolving `$secret` directives    
-   resolving `$config` injection directives
    

After this phase completes, the configuration graph contains **no configuration-time directives**.

The resulting structure is a deterministic Python dictionary representing the entire configuration graph.

----------

## 5.1 Source Merging

Configuration fragments returned by each `ConfigurationSource` are merged into a single configuration graph.

Merge semantics:

-   sources are applied in order
-   later sources override earlier sources
-   mappings are deep-merged
-   scalar values and lists replace earlier values
    
This allows configuration layering such as:

-   base configuration
-   environment-specific overrides
-   developer overrides
-   runtime overrides
    
----------

## 5.2 Secret Resolution

Secret values are resolved using `SecretResolver` implementations.

Resolvers are responsible for mapping secret identifiers to actual values.

Typical implementations may retrieve secrets from:

-   environment variables
-   secret managers
-   encrypted configuration stores
   
Secret resolution occurs during configuration loading so that secret values never appear in unresolved form during compilation.

----------

## 5.3 Configuration Injection

The `$config` directive allows configuration fragments to reference and reuse other configuration subtrees.

This enables reuse patterns such as:

-   shared component configuration
-   environment-specific overrides
-   common configuration templates
    
The `ConfigLoader` resolves these references by copying and merging the referenced configuration subtree.

----------

# 6. Phase 2: Component Compilation

**Component:** `ComponentCompiler`

The `ComponentCompiler` transforms the resolved configuration graph into a fully instantiated object graph.

This process includes:

1.  discovering component definitions
2.  building the dependency graph
3.  validating dependency correctness
4.  determining safe instantiation order
5.  constructing all components
    
The result is an immutable dependency injection container containing all configured components.

----------

# 7. Component Construction

Components are defined using **provider directives**.

Provider directives determine how a component instance is constructed.

Supported provider directives include:
| Directive | Behavior |
| -- | -- |
| `$provider` | Invoke a registered provider |
| `$class` | Construct a component using Python class reflection |

Providers encapsulate component construction logic and may perform any required initialization.

Example (YAML representation):
```yaml
database:  
 $provider: postgres.connection  
 host: localhost
```
or
```yaml
cache:  
 $class: redis.Redis  
 host: localhost
```
Although YAML is shown here, the same configuration may be produced using a Python dictionary.

----------

# 8. Dependency Graph

Dependencies between components are declared using the `$ref` directive.

A `$ref` references the identity of another component in the dependency injection container.

Example:
```yaml
service:  
 $provider: services.user  
 database:  
 $ref: database
```
During compilation the `ComponentCompiler` analyzes `$ref` usage to construct a dependency graph.

The compiler validates:

-   that referenced components exist    
-   that dependency cycles are not present
-   that components are instantiated in safe order
    
Components are then instantiated using a **topological sort** of the dependency graph.

----------

# 9. Component Identity

Each component registered in the container has a unique identity used for `$ref` resolution.

If a component definition contains the `$name` directive, that value becomes the component identity.

If `$name` is not present, the compiler derives the component identity from the **configuration path** of the component definition.

Example:
```yaml
services:  
 user_service:  
 $provider: services.user
```
Produces the component identity:
```
services.user_service
```
This naming rule guarantees deterministic component identities without requiring explicit naming.

----------

# 10. Runtime Result

After compilation:

-   all configuration directives are resolved
-   all components are instantiated
-   all references are concrete object references
-   the dependency graph is immutable
    
The runtime system interacts only with the fully constructed dependency injection container.

No configuration parsing or reference resolution occurs during runtime execution.

----------

# 11. Determinism Guarantee

Flotilla’s compilation model provides a strong guarantee:

> If the application starts successfully, the component graph is valid.

This ensures:

-   no missing dependencies
-   no circular references
-   no runtime configuration errors
-   deterministic component instantiation
    
All configuration errors are detected during compilation before the application begins execution.

----------

# 12. Relationship to the Configuration Rules Specification

This document describes the **architecture and lifecycle of configuration in Flotilla**.

The formal grammar, directive definitions, and structural validation rules are defined in the **Flotilla Configuration Rules** specification.

Developers implementing or authoring configuration should consult the rules document for detailed syntax and validation requirements.
