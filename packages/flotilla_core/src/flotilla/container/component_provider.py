from __future__ import annotations

from typing import Any, Awaitable, Callable, TypeAlias


ComponentProvider: TypeAlias = Callable[..., Any | Awaitable[Any]]
"""
Semantic type for callables that build Flotilla components.

A component provider receives already-materialized keyword arguments from the
component compiler and returns a component instance. Providers may be regular
functions, async functions, classes, or callable objects.

Providers are intentionally not passed the FlotillaContainer or raw config.
Dependency graph wiring belongs in component configuration via directives such
as ``$ref``, ``$list``, ``$map``, ``$factory``, and ``$params``. Custom object
construction logic belongs inside the provider callable itself.
"""
