1.  ### Component Declaration
    
    A configuration node becomes a DI component if and only if it declares a `builder`. A YAML path cannot exist on the DI graph without a builder. Any attempt to reference, inject, or reuse a node without a builder is an error.
    
2.  ### Builder Contract
    
    A builder is a plain Python callable. Its signature defines the component’s contract. Builders receive only concrete values and must not receive configuration objects, containers, or framework metadata.
    
3.  ### Compilation Pipeline
    
    Configuration is processed by a loader (merging sources, resolving `$secret` and `$config`, detecting cycles), then compiled into a component graph by a recursive compiler, and finally stored in the DI container.
    
4.  ### `$config` — Config-Level Component Reuse
    
    `$config` references another configuration path that must declare a builder. It reuses configuration, not runtime instances. Cycles are illegal. After resolution, `$config` becomes an embedded component definition and always results in a new component instance.
    
5.  ### `$ref` — Runtime Component Reuse
    
    `$ref` injects an existing runtime component from the DI container. It never triggers construction. The referenced component must already exist, or an error is raised. The same instance is injected wherever it is referenced.
    
6.  ### Allowed Values Under a Builder
    
    Once a builder is identified, only specific value types are allowed within that component’s configuration scope. Any other value shape is invalid.
    
7.  ### Atomic Value Types
    
    Atomic values include scalars (strings, numbers, booleans), resolved `$ref` values, resolved `$config` values, and embedded component definitions (mappings that declare a builder).
    
8.  ### Structured Values (`$list` and `$dict`)
    
    Lists and dictionaries are supported only when explicitly declared using `$list` or `$dict`. These markers make structured-data intent explicit and prevent ambiguous or accidental nesting.
    
9.  ### Rules for Structured Values
    
    Elements inside `$list` and values inside `$dict` may themselves be scalars, `$ref`, `$config`, embedded components, or nested `$list`/`$dict`. Raw lists or dictionaries without these markers are illegal under a builder.
    
10.  ### Recursive Compilation
    
    Component compilation is recursive. Embedded components are compiled before their parents. After compilation, embedded components behave identically to `$ref` injections at runtime.
    
11.  ### Secrets (`$secret`)
    
    `$secret` references are resolved during configuration loading. After loading completes, no `$secret` references may remain. Builders and compilers never see `$secret`.
    
12.  ### Container Semantics
    
    The DI container stores compiled components, resolves `$ref`, and enforces existence and uniqueness. It does not interpret configuration and does not perform wiring or compilation logic.
    
13.  ### Canonical Mental Model
    
    Configuration declares components. Builders define construction. The compiler enforces grammar. The container holds objects.