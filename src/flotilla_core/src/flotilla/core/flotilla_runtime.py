from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Optional
from flotilla.core.execution_config import ExecutionConfig
from flotilla.core.runtime_event import RuntimeEvent
from flotilla.core.runtime_result import RuntimeResult


class FlotillaRuntime(ABC):
    """
    Public execution interface for Flotilla runtimes.
    """
