import importlib
from typing import Any
from flotilla.config.errors import FlotillaConfigurationError


class ReflectionProvider:
    """
    Provider that constructs an object from a fully qualified class name.

    The provider imports the class and invokes the constructor
    with the supplied keyword arguments.
    """

    def __call__(self, class_path: str, **kwargs: Any) -> Any:
        module_name, _, class_name = class_path.rpartition(".")

        if not module_name:
            raise FlotillaConfigurationError(f"Invalid class path '{class_path}'")

        module = importlib.import_module(module_name)

        try:
            cls = getattr(module, class_name)
        except AttributeError as exc:
            raise FlotillaConfigurationError(f"Class '{class_name}' not found in module '{module_name}'") from exc

        return cls(**kwargs)
