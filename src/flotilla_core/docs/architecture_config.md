# Flotilla Architecture Overview

## What is Flotilla?

Flotilla is a **declarative component graph specification language** that compiles YAML configuration into a fully-instantiated dependency injection container.

### Key Insight

Flotilla does not interpret YAML dynamically at runtime. Instead, it treats configuration as **code that compiles** into a deterministic object graph before your application runs.

This means:
- Configuration errors are caught at startup, not at runtime
- No symbolic references or indirection during execution
- Guaranteed valid dependency graph if compilation succeeds

---

## Two-Phase Compilation Pipeline

```
YAML Configuration
        ↓
   ConfigLoader
   (Phase 1: Resolve symbolic config)
        ↓
Resolved Configuration
        ↓
  ComponentCompiler
  (Phase 2: Build object graph)
        ↓
  DI Container
        ↓
Runtime Execution
(pure behavior, zero config overhead)
```

Each phase has strict responsibilities and provides specific guarantees about what the next phase receives.

---

## Phase 1: Configuration Resolution

**Component:** `ConfigLoader`

**Mission:** Transform raw YAML sources into a single, fully-resolved configuration tree with all symbolic references eliminated.

### What Gets Resolved

The ConfigLoader handles configuration-time concerns:

- **Multi-source merging** - Combine multiple config files with deterministic override semantics
- **Secret resolution** - Replace `$secret` directives with actual values from secret stores
- **Config injection** - Resolve `$config` references that inject configuration subtrees
- **Environment substitution** - Handle environment variable references

### Why This Matters

After ConfigLoader runs, you have a **concrete configuration tree** with:
- No references to other config sections
- No unresolved secrets
- No environment-dependent tokens
- Complete determinism - the same config tree every time

### Output Contract

The ConfigLoader produces `FlotillaSettings` containing a fully-resolved dictionary. This dictionary is **immutable** and ready for the compiler.

**Guarantee:** No configuration-time directives (`$secret`, `$config`) remain.

---

## Phase 2: Component Compilation

**Component:** `ComponentCompiler`

**Mission:** Build a validated dependency graph and instantiate all components in the correct order.

### The Component Graph Model

Flotilla treats your configuration as a **component graph specification**:

- Each `factory` node defines a component
- `$ref` directives create edges in the dependency graph
- The compiler validates the graph (no cycles, no missing dependencies)
- Components are instantiated in topological order

### What Gets Compiled

The ComponentCompiler transforms directive nodes into concrete objects:

- **Component definitions** (`factory` nodes) → Instantiated objects
- **`$ref` directives** → References to already-instantiated components
- **`$list` directives** → Python lists containing resolved values
- **`$map` directives** → Python dictionaries containing resolved values

### The Compilation Process

1. **Discovery** - Scan the config tree and register all component definitions
2. **Graph Construction** - Build the dependency graph by analyzing `$ref` usage
3. **Validation** - Detect cycles, missing references, and structural errors
4. **Topological Sort** - Determine safe instantiation order
5. **Instantiation** - Create components, materializing all directives

### Why This Matters

The compiler catches errors **before your application runs**:
- Missing component references
- Circular dependencies
- Invalid factory signatures
- Type mismatches

If compilation succeeds, you're guaranteed a valid object graph.

### Output Contract

The ComponentCompiler produces an **immutable DI container** containing fully-instantiated components.

**Guarantee:** No directives (`$ref`, `$list`, `$map`) or raw data structures remain - only concrete Python objects.

---

## Phase Boundaries and Guarantees

Each phase eliminates certain types of symbolic references, progressively transforming the configuration into concrete objects.

### After Phase 1 (ConfigLoader)

**Input:** Raw YAML with config-time directives  
**Output:** Fully-resolved configuration tree

**Eliminated:**
- `$secret` directives
- `$config` references
- Environment variables
- Multi-source ambiguity

**Result:** A single, deterministic configuration dictionary ready for compilation.

### After Phase 2 (ComponentCompiler)

**Input:** Resolved configuration with component directives  
**Output:** Immutable DI container with instantiated objects

**Eliminated:**
- `$ref` directives
- `$list` wrappers
- `$map` wrappers
- Raw lists and dicts (enforced structural validation)
- `factory` definitions (replaced with instances)

**Result:** A fully-instantiated object graph with zero indirection.

---

## The Determinism Guarantee

Flotilla's compilation approach provides a critical guarantee:

> **If your application starts successfully, your entire component graph is valid.**

This means:

### No Runtime Wiring Failures

All dependencies are resolved at compile time. You'll never encounter:
- "Component not found" errors during execution
- Null reference exceptions from missing dependencies
- Late-bound configuration errors

### Fail Fast

All configuration and wiring errors are detected **before** your application code runs:
- Missing components are caught during compilation
- Circular dependencies are detected immediately
- Invalid factory signatures fail early
- Type mismatches are found before execution

### Zero Configuration Overhead at Runtime

Once compiled:
- No symbolic lookups
- No lazy resolution
- No configuration parsing
- Pure object references and method calls

Your application runs with the same performance as if you had hand-wired all dependencies in code.

### Predictable Behavior

The same configuration always produces:
- The same dependency graph
- The same instantiation order
- The same object identities
- The same runtime behavior

No hidden state, no environment-dependent surprises.

---

## Design Philosophy

### Configuration as Code

Flotilla treats configuration not as data, but as **code that compiles**.

Traditional configuration systems:
- Parse config files at runtime
- Look up values dynamically
- Wire dependencies on-demand
- Fail late with cryptic errors

Flotilla instead:
- Compiles configuration into code
- Validates all dependencies upfront
- Instantiates the full graph before execution
- Fails early with clear error messages

### Explicit Over Implicit

Flotilla rejects "convention over configuration" in favor of "explicit over implicit":

- **No magic** - Every component, dependency, and collection must be declared
- **No shortcuts** - Raw lists and dicts are forbidden; use `$list` and `$map`
- **No surprises** - What you see in the config is exactly what you get at runtime

### Structural Enforcement

The configuration grammar is **intentionally restrictive**:

- Only specific node types are allowed
- Free-form nested structures are forbidden
- Every mapping must have a clear purpose (`factory`, directive, or scalar)

This rigidity ensures:
- Configurations are machine-readable and analyzable
- Tooling can provide intelligent validation
- Refactoring is safe and predictable

### Compile-Time Validation

By catching all errors at compile time, Flotilla enables:
- **Confident deployments** - If it compiles, it works
- **Fast feedback** - Errors appear immediately, not in production
- **Better testing** - Integration tests can assume valid wiring

---

## Why This Architecture Matters

### For Developers

- **Write once, run correctly** - Valid config means valid runtime behavior
- **Refactor safely** - The compiler catches breaking changes immediately
- **Debug easily** - Clear error messages at compile time, not cryptic runtime failures
- **Test confidently** - No need to test wiring; focus on business logic

### For Operations

- **Deploy safely** - Failed compilation prevents bad deploys
- **Understand dependencies** - The component graph is explicit and analyzable
- **Troubleshoot quickly** - No hidden configuration state or lazy loading surprises

### For System Design

- **Enforce boundaries** - Components can only depend on explicitly declared dependencies
- **Control complexity** - The dependency graph is visible and validated
- **Enable tooling** - IDEs, linters, and visualizers can understand the config

---

## Mental Model

Think of Flotilla configuration like TypeScript or Rust:

1. **You write code** (configuration DSL)
2. **The compiler validates it** (ConfigLoader + ComponentCompiler)
3. **You get artifacts** (DI Container)
4. **You run the artifacts** (your application)

The configuration **is not read at runtime**. It's **compiled into runtime**.

---

## When to Use Flotilla

Flotilla is ideal when you need:

- **Complex dependency graphs** - Many components with intricate wiring
- **High reliability requirements** - Can't afford runtime wiring failures
- **Large teams** - Need clear contracts and safe refactoring
- **Long-lived systems** - Want maintainable, understandable configuration

Flotilla may be overkill for:

- Simple applications with few dependencies
- Prototypes where flexibility matters more than validation
- Systems that need truly dynamic runtime configuration

---

## Further Reading

For detailed syntax rules, directive specifications, and grammar requirements, see the **Flotilla Configuration Rules** documentation.

This overview provides the conceptual foundation; the rules document provides the technical specification.