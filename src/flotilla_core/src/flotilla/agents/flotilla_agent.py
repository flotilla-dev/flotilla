from abc import ABC, abstractmethod
from typing import AsyncIterator
from flotilla.core.agent_event import AgentEvent
from flotilla.core.execution_config import ExecutionConfig
from flotilla.core.thread_context import ThreadContext, ThreadStatus
from flotilla.agents.agent_errors import ThreadIdMismatchError, InvalidAgentEventError
from flotilla.core.agent_event import AgentEventType, AgentEvent


class FlotillaAgent(ABC):
    """
    Stateless reasoning engine.

    - Consumes ThreadContext
    - Emits AgentEvent stream
    - Performs no persistence
    - Owns no lifecycle transitions
    """

    def __init__(self, *, agent_name: str):
        if not agent_name:
            raise ValueError("agent_name must be a non-empty string")
        self._agent_name = agent_name

    @property
    def agent_name(self) -> str:
        return self._agent_name

    async def initialize(self) -> None:
        """
        Optional lifecycle hook.
        Called once after construction.
        """
        return None

    async def shutdown(self) -> None:
        """
        Optional lifecycle hook.
        Called during teardown.
        """
        return None

    async def run(
        self,
        thread: ThreadContext,
        config: ExecutionConfig,
    ) -> AsyncIterator[AgentEvent]:
        if thread.status != ThreadStatus.RUNNABLE:
            raise ThreadNotRunnableError(thread.status)

        if config.thread_id != thread.thread_id:
            raise ThreadIdMismatchError(
                expected=config.thread_id,
                actual=thread.thread_id,
            )

        async for event in self._execute(thread, config):
            yield event

    @abstractmethod
    async def _execute(
        self,
        thread: ThreadContext,
        config: ExecutionConfig,
    ) -> AsyncIterator[AgentEvent]: ...
