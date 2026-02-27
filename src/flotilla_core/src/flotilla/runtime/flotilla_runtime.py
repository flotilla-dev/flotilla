from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Optional
from flotilla.runtime.execution_config import ExecutionConfig
from flotilla.runtime.runtime_event import RuntimeEvent
from flotilla.runtime.runtime_response import RuntimeResponse


class FlotillaRuntime(ABC):
    """
    Public execution interface for Flotilla runtimes.
    """
