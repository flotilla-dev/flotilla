# Flotilla Configuration Rules

>  **Note:** This document provides the detailed technical specification of Flotilla's configuration grammar. For a conceptual overview of how Flotilla works and why it's designed this way, see the **Flotilla Architecture Overview**.
---
## Overview

Flotilla configuration is a **declarative component graph specification language**, not arbitrary YAML, generic JSON, or loosely-typed config. It compiles YAML into a component graph of components defined by provider directives.
 

**Core Philosophy:**
- Explicit is required
- Implicit is forbidden
- Structure is enforced
- Slop is rejected
---
## Component Identity and Default Naming

Each component registered in the DI container has a **component identity** used for `$ref` resolution.

----------

### Default Naming Convention

By default the compiler derives the component name from the **configuration path** of the component definition.

The path is constructed by joining the mapping keys from the root of the configuration tree to the component node.

Example:
```yaml
services:  
 user_service:  
 $provider: services.user
```
Default component name:
```python
services.user_service
```
----------

### Nested Components

Nested components follow the same rule.

Example:
```yaml
agent:  
 $provider: agents.weather  
 llm:  
	 $provider: llm.openai
```
Component names produced by the compiler:
```python
agent  
agent.llm
```
----------

### `$name` Override

If `$name` is provided, it overrides the default path-based name.

Example:
```yaml
agent:  
	$provider: agents.weather  
	llm:  
		$provider: llm.openai  
		$name: weather_llm
```
Registered component names:
```python
agent  
weather_llm
```
----------

### Naming Invariants

-   Component names **must be unique**
-   Duplicate names cause a compilation error
-   `$ref` resolution uses the final component identity


## Directives

### $secret

**Purpose:** Resolve a secure scalar value from a SecretResolver

**Resolution Phase:** ConfigLoader

**Rules:**
- Must resolve to a scalar value
- May appear anywhere a value is allowed
- Must be fully resolved before compilation
- Unresolved `$secret` → `SecretResolutionError`  

**Syntax:**
```yaml
arg:
	$secret: SECRET_KEY
```
**Requirements:**
- MUST be a mapping node
- MUST contain only `$secret`
- Value MUST be string
  
**Invariant:** No `$secret` may exist after `ConfigLoader.load()`

  ---
### $config

**Purpose:** Inject configuration anchored at a named path elsewhere in the config

**Resolution Phase:** ConfigLoader

**Syntax:**
```yaml
llm:
	$config: llm.openai
	overrides:
		max_tokens: 5000
```
**Meaning:**
- Resolve `llm.openai`
- Deep-copy the referenced config subtree
- Deep-merge the `overrides` mapping on top (last-wins)
- Recursively resolve any nested `$config`

**Disallowed Form:**
```yaml
llm:
	$config: llm.openai
	max_tokens: 5000  # ❌ Illegal - arbitrary sibling keys not allowed
```
**Rules:**
- MUST be a mapping node
- MUST contain `$config`
- MAY contain `overrides`
- No other keys allowed
- May appear anywhere in the config tree
- Resolution is recursive and must reach a fixpoint
- Referenced paths must exist
- Injects structure via deep copy, not references
- Unresolved `$config` → `ConfigurationResolutionError`
 
**Invariant:** No `$config` may exist after `ConfigLoader.load()`

  ---
 
### $provider
 
**Purpose**: Construct a component using a registered provider in the DI container.  Custom Providers are registered via the FlotillaApplication.register_provider() method

**Resolution Phase**: ComponentCompiler

**Syntax**:
```yaml
component:
	$provider: provider.identifier
	arg1: value
	arg2: value
```
  
Rules:
- MUST be a mapping node
- MUST contain `$provider`
- Value MUST be a string
- Other keys are interpreted as constructor keyword arguments
-  `$provider` MUST NOT appear with `$class`, other directives are allowed
---


### $class

**Purpose**: Construct a component using Python class reflection.  This is a short cut for the $provider usage where the Provider is assumed to be the automatically registered ReflectionProvider

**Resolution Phase**: ComponentCompiler

**Syntax**:
  
```yaml
component:
	$class: package.module.ClassName
	arg1: value
```
  
**Rules**:
- MUST be a mapping node
- MUST contain `$class`
- Value MUST be a string
- Other keys are interpreted as constructor keyword arguments
-  `$class` MUST NOT appear with `$provider`, other directives are allowed

---
### $name

**Purpose**: Override the default component identity.  

**Resolution Phase**: ComponentCompiler

**Syntax**:
```yaml
component:
  $provider: example.provider
  $name: custom_component_name
```
**Rules**:
- Optional
- Value MUST be string
---

### $ref

**Purpose:** Reference a component instance in the DI container.  TThe name of the component is the `$name` value if present, otherwise the component key.

**Resolution Phase:** ComponentCompiler

**Canonical Rule:** { `$ref: <token>` } is valid if and only if `<token>` resolves to a component retrievable via `FlotillaContainer.get(<token>)`

**Syntax:**

```yaml
arg:
	$ref: component_name
```

**Rules:**
- MUST be a mapping node
- MUST contain only the key `$ref`
- Value MUST be a string
-  **Scalar form (`"$ref component"`) is invalid**
- Is a compiler instruction, not a data value
- Must be resolved during compilation
- May not reach runtime or factory invocation
- Missing or invalid `$ref` → `ReferenceResolutionError`
---

### $list

**Purpose:** Declare an ordered collection of values and/or `$ref` entries

**Resolution Phase:** ComponentCompiler

**Syntax:**

```yaml
arg:
	$list:
	- <value>
	- <value>
```

**Rules:**
- MUST be a mapping node
- MUST contain only the key `$list`
- Value MUST be a YAML list
-  **Raw lists (`[1,2,3]`) are invalid**
- Elements may include:
-  `$ref <component>`
- scalars
- embedded components
- All `$ref` entries must resolve
- Each element must conform to the Flotilla grammar

---

### $map

**Purpose:** Declare a mapping of values and/or `$ref` entries

**Resolution Phase:** ComponentCompiler

**Syntax:**
```yaml
arg:
	$map:
		key1: <value>
		key2: <value>
```

**Rules:**
- MUST be a mapping node
- MUST contain only the key `$map`
- Value MUST be a YAML mapping
-  **Raw dicts used as free-form nested objects are invalid**
- Values may include:
- { `$ref: <component>` }
- scalars
- embedded components
- All `$ref` entries must resolve
- Each value must conform to the Flotilla grammar

---

  

## Allowed Node Types

### Component Definition Node

A component definition is a mapping node containing exactly one provider directive.

Supported provider directives:
-   `$provider` — constructs the component using a provider registered in the `FlotillaContainer`    
-   `$class` — constructs the component using Python class reflection
    
A component definition mapping:

-   MUST contain exactly one provider directive (`$provider` or `$class`)
-   MAY contain `$name`**, which overrides the component identity
-   MAY contain additional keys, interpreted as constructor keyword arguments
-   MUST NOT contain any other directive keys at the same mapping level
    
Constructor argument values may themselves contain valid nested directives such as `$ref`, `$list`, `$map`, `$provider`, or `$class`, so long as those nested values independently conform to the Flotilla grammar.

**Structure**:
```yaml
component_name:
	$provider: <provider.identifier>
	<argument_key>: <value>
	$name: <optional_override_name>
```
  
**Rules:**

- MUST contain `$provider`
- MAY contain `$name`
- Other keys are interpreted as constructor keyword arguments
- Argument values must themselves conform to the Flotilla grammar

---

### Scalars

**Allowed scalar values:**
- string (non-directive)
- int
- float
- bool
- null

**Disallowed scalar values:**

-  `$provider something`
-  `$name something`
-  `$ref something`
-  `$list something`
-  `$map something`
-  `$config something`
-  `$secret something`

**All directives must be mapping-form.**

---

## Embedded Component Definitions

### Rule

A component definition node (mapping containing `$provider` or `$class`)  
MAY appear anywhere a value is allowed.

- As a top-level component
- As a constructor argument to another component
- As an element inside `$list`
- As a value inside `$map`

### Example

**Nested component definition:**
```yaml
agent:
	$provider: agents.weather_agent
	llm:
		$provider: llm.openai
		model: gpt-4o-mini
```

This defines a nested component. The nested `llm` component is treated identically to a top-level component definition.


### Additional Examples

**Inside `$list`:**

```yaml

pipeline:
	$provider: pipeline.sequential
	stages:
		$list:
			- $provider: stages.preprocessor
				arg: basic
			- $provider: stages.analyzer
				arg: advanced
```

**Inside `$map`:**

```yaml
router:
	$provider: routing.conditional_router
	handlers:
		$map:
			success:
				$provider: handlers.success_handler
			failure:
				$provider: handlers.error_handler
```

---

## Illegal Structures

### Raw Lists

```yaml
arg: [1, 2, 3] # ❌ Illegal
```
Must use:

```yaml
arg:
	$list:
		- 1
		- 2
		- 3
```

### Raw Arbitrary Dicts

```yaml
arg:
	foo: bar
	baz: qux  # ❌ Illegal (free-form JSON-style nested maps)
```

Must use:
```yaml
arg:
	$map:
		foo: bar
		baz: qux
```

---
## Configuration Graph Construction

Before component compilation, Flotilla constructs a **resolved configuration graph** using the `ConfigLoader`.

The `ConfigLoader` is responsible for:

1.  Loading configuration fragments
2.  Merging fragments into a single configuration tree   
3.  Resolving `$secret` values
4.  Resolving `$config` injections
    
After this phase, the configuration is **fully materialized** and ready for compilation.

----------

### Configuration Sources

Configuration fragments are provided by objects implementing the `ConfigurationSource` protocol.
```python
class  ConfigurationSource(Protocol):  
  def  load(self) -> Dict[str, Any]
```
Each source returns a mapping containing a configuration fragment.

Examples of configuration sources may include:

-   YAML files
-  Python Dict object
-   environment-derived configuration
-   remote configuration services
-   test configuration fixtures
    
----------

### Source Merging

The `ConfigLoader` loads all sources and merges them into a single configuration tree.

Merge semantics:

-   Sources are applied **in order**    
-   Later sources override earlier ones
-   Mappings are **deep merged**
-   Scalars and lists **replace earlier values**
    
This produces a single deterministic configuration dictionary.

----------

### Secret Resolution

Secret values are resolved using `SecretResolver` implementations.

```python
class  SecretResolver(Protocol):  
  def  resolve(self, secret_key: str) -> Any  |  None
```
Each resolver is queried in order.

Resolution behavior:

-   If a resolver returns a value, it is considered resolved    
-   If multiple resolvers return values, the **last non-None result wins**
-   If no resolver resolves the secret, loading fails
    
Secrets must appear in mapping form:

```yaml
password:  
 $secret: DATABASE_PASSWORD
```
----------

### `$config` Resolution

`$config` allows one configuration subtree to reference another.

Example:
```yaml
llm:  
 $config: llm.openai  
 overrides:  
 max_tokens: 5000
```

Resolution process:

1.  Locate the referenced config path    
2.  Deep-copy the referenced subtree
3.  Apply overrides
4.  Recursively resolve nested `$config`
    
----------

### Final Output of ConfigLoader

After `ConfigLoader.load()`:

-   All `$secret` directives are resolved
-   All `$config` directives are resolved
-   The configuration tree contains **only concrete values**
    
The result is wrapped in `FlotillaSettings` and passed to the `ComponentCompiler`.


## Phase Separation

### ConfigLoader Phase

**Resolves:**
-  `$config`
-  `$secret`
- Environment substitution
- Config source merging

**Guarantees:**
- No `$config` remains
- No `$secret` remains
- Configuration is fully resolved and deterministic

### ComponentCompiler Phase

**Resolves:**

- `$provider`
- `$class`
- `$name`
-  `$ref`
-  `$list`
-  `$map`


**Builds:**
- Dependency graph
- Topologically sorted component instantiation
- Immutable DI container

**Guarantees:**
- No directives remain
- No raw lists
- No raw dicts
- Only concrete component instances exist

The compiler must recursively discover and register all component definition nodes (provider directives), regardless of depth.

---

## Phase Ownership Summary

| Token | Meaning | Resolved by | May reach runtime |
|-------|---------|-------------|-------------------|
| `$secret` | Secure scalar value | ConfigLoader | ❌ |
| `$config` | Config subtree injection | ConfigLoader | ❌ |
| `$provider` | Custom component creation logic | ComponentCompiler | ❌ |
| `$class` | Full class name of the component to create via reflection | ComponentCompiler | ❌ |
| `$name` | Name of the component on the DI container, overrides default naming convention | ComponentCompiler | ❌ |
| `$ref` | Component identity | ComponentCompiler | ❌ |
| `$list` | Component/value collection | ComponentCompiler | ❌ |
| `$map` | Component/value mapping | ComponentCompiler | ❌ |

---

## Global Invariants

**After ConfigLoader:**

- ❌ No `$secret`
- ❌ No `$config`

**After ComponentCompiler:**

- ❌ No `$ref`
- ❌ No raw lists
- ❌ No raw dicts

**Runtime sees:**

- ✅ Fully concrete config
- ✅ Fully instantiated components
- ✅ No symbolic directives

---

## Canonical Structural Rule

**A mapping node is valid if and only if it satisfies exactly one of:**

1. Contains exactly one provider directive (`$provider` or `$class`)
2. Contains exactly one structural directive (`$ref`, `$list`, `$map`)
3. Contains exactly one configuration directive (`$config`, `$secret`)

This rule applies uniformly at all depths in the configuration tree.

**Any other mapping node is invalid.**

---

## Determinism Guarantee

If the application starts successfully:

- The graph is valid
- All dependencies are resolvable
- No symbolic references remain
- No runtime wiring errors can occur

**At the end of compilation:**

- The runtime sees no DSL constructs
- All references are resolved
- All wiring errors are detected before execution
- Runtime execution is free of configuration indirection