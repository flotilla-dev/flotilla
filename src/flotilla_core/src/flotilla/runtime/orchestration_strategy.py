from abc import ABC, abstractmethod
from flotilla.thread.thread_context import ThreadContext
from flotilla.runtime.execution_config import ExecutionConfig
from flotilla.agents.agent_event import AgentEvent
from typing import AsyncIterator


class OrchestrationStrategy(ABC):

    @abstractmethod
    async def execute(
        thread_context: ThreadContext, execution_config: ExecutionConfig
    ) -> AsyncIterator[AgentEvent]:
        pass
