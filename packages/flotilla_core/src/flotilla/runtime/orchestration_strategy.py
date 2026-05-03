from abc import ABC, abstractmethod
from flotilla.thread.thread_context import ThreadContext
from flotilla.runtime.phase_context import PhaseContext
from flotilla.agents.agent_event import AgentEvent
from typing import AsyncIterator


class OrchestrationStrategy(ABC):
    """
    Strategy that runs application orchestration for an active runtime phase.

    FlotillaRuntime invokes this after it has appended the initiating
    ThreadEntry and reloaded durable thread state. The strategy receives the
    current ThreadContext plus PhaseContext and streams AgentEvent objects back
    to the runtime.

    Implementations coordinate agents and tools, but must not append directly
    to the ThreadEntryStore. Runtime remains responsible for converting
    terminal AgentEvents into durable ThreadEntry records.
    """

    @abstractmethod
    async def execute(
        self, thread_context: ThreadContext, phase_context: PhaseContext
    ) -> AsyncIterator[AgentEvent]:
        pass
