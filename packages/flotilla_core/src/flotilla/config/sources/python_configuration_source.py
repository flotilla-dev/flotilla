from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable
from typing import Any, Dict

from flotilla.config.config_utils import ConfigUtils


class PythonConfigurationSource:
    """
    ConfigurationSource that loads configuration fragments from Python callables.

    Callables are evaluated in order and deep-merged using ConfigLoader source
    semantics. Each callable may be sync or async.

    A configuration callable is intentionally lightweight: it returns component
    and factory *definitions* as dictionaries. It does not build runtime
    objects. Providers and factory bindings perform object construction later,
    during component compilation or binding resolution.
    """

    def __init__(self, functions: Callable[[], Dict[str, Any]] | Iterable[Callable[[], Dict[str, Any]]]):
        if callable(functions):
            self._functions = [functions]
        else:
            self._functions = list(functions)

        if not self._functions:
            raise ValueError("At least one configuration function is required")

        for fn in self._functions:
            if not callable(fn):
                raise TypeError("PythonConfigurationSource requires callable configuration functions")

    @classmethod
    def from_object(cls, obj: Any, *, methods: Iterable[str]) -> "PythonConfigurationSource":
        functions = []
        for method_name in methods:
            method = getattr(obj, method_name)
            if not callable(method):
                raise TypeError(f"{method_name} is not callable")
            functions.append(method)
        return cls(functions)

    async def load(self) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        for fn in self._functions:
            fragment = fn()
            if inspect.isawaitable(fragment):
                fragment = await fragment
            if not fragment:
                continue
            if not isinstance(fragment, dict):
                raise TypeError("Python configuration functions must return dictionaries")
            merged = ConfigUtils.deep_merge(merged, fragment)
        return merged
