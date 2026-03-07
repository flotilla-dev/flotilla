from abc import ABC, abstractmethod
from flotilla.thread.thread_context import ThreadContext
from flotilla.runtime.phase_context import PhaseContext
from flotilla.agents.agent_event import AgentEvent
from typing import AsyncIterator


class OrchestrationStrategy(ABC):

    @abstractmethod
    async def execute(
        thread_context: ThreadContext, phase_context: PhaseContext
    ) -> AsyncIterator[AgentEvent]:
        pass
