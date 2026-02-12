# Flotilla Configuration Rules

> **Note:** This document provides the detailed technical specification of Flotilla's configuration grammar. For a conceptual overview of how Flotilla works and why it's designed this way, see the **Flotilla Architecture Overview**.

---

## Overview

Flotilla configuration is a **declarative component graph specification language**, not arbitrary YAML, generic JSON, or loosely-typed config. It compiles YAML into a deterministic graph of components defined by factory nodes.

**Core Philosophy:**
- Explicit is required
- Implicit is forbidden
- Structure is enforced
- Slop is rejected

---

## Configuration Directives

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

### $ref

**Purpose:** Reference a component instance in the DI container

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
- **Scalar form (`"$ref component"`) is invalid**
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
- **Raw lists (`[1,2,3]`) are invalid**
- Elements may include:
  - `$ref <component>`
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
- **Raw dicts used as free-form nested objects are invalid**
- Values may include:
  - { `$ref: <component>` }
  - scalars
  - embedded components
- All `$ref` entries must resolve
- Each value must conform to the Flotilla grammar

---

## Allowed Node Types

### Component Definition Node

A mapping node containing a `factory` key.

**Structure:**
```yaml
component_name:
  factory: <factory.identifier>
  <argument_key>: <value>
  ref_name: <optional_override_name>
```

**Rules:**
- MUST contain `factory`
- MAY contain `ref_name`
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
- `$ref something`
- `$list something`
- `$map something`
- `$config something`
- `$secret something`

**All directives must be mapping-form.**

---

## Embedded Component Definitions

### Rule

A component definition node (mapping containing `factory`) MAY appear anywhere a value is allowed, including:

- As a top-level component
- As a constructor argument to another component
- As an element inside `$list`
- As a value inside `$map`

### Example

**Nested component definition:**
```yaml
agent:
  factory: agents.weather_agent
  llm:
    factory: llm.openai
    model: gpt-4o-mini
```

This defines a nested component. The nested `llm` component is treated identically to a top-level component definition.

### Additional Examples

**Inside `$list`:**
```yaml
pipeline:
  factory: pipeline.sequential
  stages:
    $list:
      - factory: stages.preprocessor
        config: basic
      - factory: stages.analyzer
        model: advanced
```

**Inside `$map`:**
```yaml
router:
  factory: routing.conditional_router
  handlers:
    $map:
      success:
        factory: handlers.success_handler
      failure:
        factory: handlers.error_handler
```


---

## Illegal Structures

### Raw Lists
```yaml
arg: [1, 2, 3]  # ❌ Illegal
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

Unless it is:
- A component definition (contains `factory`)
- A directive (`$ref`, `$list`, `$map`, `$config`, `$secret`)

---

## Phase Separation

### ConfigLoader Phase

**Resolves:**
- `$config`
- `$secret`
- Environment substitution
- Config source merging

**Guarantees:**
- No `$config` remains
- No `$secret` remains
- Configuration is fully resolved and deterministic

### ComponentCompiler Phase

**Resolves:**
- `$ref`
- `$list`
- `$map`

**Builds:**
- Dependency graph
- Topologically sorted component instantiation
- Immutable DI container

**Guarantees:**
- No directives remain
- No raw lists
- No raw dicts
- Only concrete component instances exist

The compiler must recursively discover and register all component definition nodes (factory nodes), regardless of depth.
---

## Phase Ownership Summary

| Token | Meaning | Resolved by | May reach runtime |
|-------|---------|-------------|-------------------|
| `$secret` | Secure scalar value | ConfigLoader | ❌ |
| `$config` | Config subtree injection | ConfigLoader | ❌ |
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

1. Contains `factory` (component definition)
2. Contains exactly one of: `$ref`, `$list`, `$map`, `$config`, `$secret`
3. This rule applies uniformly at all depths in the configuration tree.

**Any other mapping node is invalid.**

---

## Component Definition vs Directive Exclusivity

### Principle

A mapping node must represent exactly one semantic role.

### Rule

A mapping node MUST NOT mix component-definition keys and directive keys.

Specifically:

- A mapping node that contains `factory` MUST NOT contain any directive keys:
  - `$ref`
  - `$list`
  - `$map`
  - `$config`
  - `$secret`

- A mapping node that contains a directive key (`$ref`, `$list`, `$map`, `$config`, `$secret`) MUST NOT contain any other keys except those explicitly allowed by that directive
  - Example: `$config` may contain `overrides`
  - Example: `$ref`, `$list`, `$map`, `$secret` must be the only key

### Illegal Examples

**Mixing factory with directive:**
```yaml
component:
  factory: some.factory
  $ref: other_component   # ❌ Illegal — mixed semantic roles
```

**Directive with extra keys:**
```yaml
arg:
  $ref: component
  other: value            # ❌ Illegal — directive node with extra keys
```

**Raw mappings:**
```yaml
arg:
  foo: bar              # ❌ Illegal — raw mapping without factory or directive
```


### Legal Examples

**Component definition:**
```yaml
component:
  factory: some.factory
  arg: 42
```

**Pure directive:**
```yaml
arg:
  $ref: component
```

### Rationale

This rule enforces a one-to-one mapping between configuration structure and semantic meaning, eliminating ambiguity and preventing accidental mixing of wiring and construction concerns.

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