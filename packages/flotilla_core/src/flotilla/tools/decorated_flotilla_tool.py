import inspect

from flotilla.tools.flotilla_tool import FlotillaTool
from flotilla.tools.tool_decorators import _TOOL_MARKER


class DecoratedFlotillaTool(FlotillaTool):
    def __init_subclass__(cls):
        super().__init_subclass__()

        execution_method_name = None

        # Walk MRO from base to subclass
        for base in reversed(cls.__mro__):
            for name, value in base.__dict__.items():
                if getattr(value, "__flotilla_tool__", None) is _TOOL_MARKER:
                    execution_method_name = name

        if execution_method_name is None:
            raise TypeError(
                f"{cls.__name__} must define exactly one @tool_call method "
                f"(directly or inherited)."
            )

        # Ensure only one unique decorated method exists
        decorated_methods = [
            name
            for base in cls.__mro__
            for name, value in base.__dict__.items()
            if getattr(value, "__flotilla_tool__", None) is _TOOL_MARKER
        ]

        unique_methods = set(decorated_methods)

        if len(unique_methods) > 1:
            raise TypeError(
                f"{cls.__name__} defines multiple @tool_call methods: "
                f"{unique_methods}"
            )

        cls._execution_method_name = execution_method_name

    @property
    def execution_callable(self):
        return getattr(self, self._execution_method_name)
