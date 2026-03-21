from __future__ import annotations
from abc import ABC
from typing import Any, Dict


class FlotillaError(RuntimeError, ABC):
    """
    Base class for all Flotilla runtime errors.
    Provides structured context for telemetry.
    """

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.context: Dict[str, Any] = context

    @property
    def error_code(self) -> str | None:
        """
        Optional stable machine-readable error code.
        Subclasses may override.
        """
        return None
