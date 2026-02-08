from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Optional
from flotilla.core.agent_input import AgentInput
from flotilla.core.execution_config import ExecutionConfig
from flotilla.core.execution_checkpoint import ExecutionCheckpoint
from flotilla.core.runtime_event import RuntimeEvent
from flotilla.core.runtime_result import RuntimeResult

class FlotillaRuntime(ABC):
    """
    Public execution interface for Flotilla runtimes.
    """

    @abstractmethod
    async def run(
        self,
        *,
        agent_input: AgentInput,
        execution_config: ExecutionConfig,
        checkpoint: Optional[ExecutionCheckpoint] = None,
    ) -> RuntimeResult:
        """
        Execute or continue an execution and return a terminal result.

        - checkpoint=None → start a new execution
        - checkpoint provided → resume a paused execution
        """
        raise NotImplementedError

    @abstractmethod
    async def stream(
        self,
        *,
        agent_input: AgentInput,
        execution_config: ExecutionConfig,
        checkpoint: Optional[ExecutionCheckpoint] = None,
    ) -> AsyncIterator[RuntimeEvent]:
        """
        Stream execution events.

        Runtimes that do not support incremental streaming MUST still
        emit at least one RuntimeEvent and then complete.
        """
        raise NotImplementedError
