from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional
from flotilla.agents.agent_event import AgentEvent
from flotilla.runtime.phase_context import PhaseContext
from flotilla.thread.thread_context import ThreadContext, ThreadStatus
from flotilla.runtime.content_part import ContentPart
from flotilla.agents.agent_errors import ThreadIdMismatchError, ThreadNotRunnableError
from flotilla.agents.agent_event import AgentEvent


class FlotillaAgent(ABC):
    """
    Stateless participant that produces AgentEvents for an orchestration phase.

    OrchestrationStrategy implementations call agents after FlotillaRuntime has
    created a PhaseContext and loaded the durable ThreadContext. An agent reads
    that context, performs model/tool work, and streams AgentEvent objects such
    as message chunks, terminal output, suspend, or error.

    Agents do not append ThreadEntry records and do not own runtime lifecycle
    transitions. Runtime converts terminal AgentEvents into durable entries.
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
        thread_context: ThreadContext,
        phase_context: PhaseContext,
        input_parts: Optional[List[ContentPart]] = None,
    ) -> AsyncIterator[AgentEvent]:
        if thread_context.status != ThreadStatus.RUNNING:
            raise ThreadNotRunnableError(thread_context.status)

        if phase_context.thread_id != thread_context.thread_id:
            raise ThreadIdMismatchError(
                expected=phase_context.thread_id,
                actual=thread_context.thread_id,
            )

        async for event in self._execute(thread_context, phase_context, input_parts=input_parts):
            yield event

    @abstractmethod
    async def _execute(
        self,
        thread: ThreadContext,
        phase_context: PhaseContext,
        input_parts: Optional[List[ContentPart]] = None,
    ) -> AsyncIterator[AgentEvent]: ...
