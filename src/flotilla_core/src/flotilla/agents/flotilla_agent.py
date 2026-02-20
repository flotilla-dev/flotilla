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

    def __init__(self):
        self.initialize()

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
            self._validate_event(event)
            yield event

    def _validate_event(self, event: AgentEvent) -> None:
        t = event.type

        if t in (AgentEventType.MESSAGE_CHUNK, AgentEventType.MESSAGE_FINAL):
            if event.role is None:
                raise InvalidAgentEventError(f"{t} requires role.")
            if not event.content:
                raise InvalidAgentEventError(f"{t} requires non-empty content.")

        if t == AgentEventType.MESSAGE_START:
            if event.role is not None or event.content is not None:
                raise InvalidAgentEventError(
                    "message_start must not include role/content."
                )

        if t == AgentEventType.SUSPEND:
            if event.role is not None or event.content is not None:
                raise InvalidAgentEventError("suspend must not include role/content.")

        if t == AgentEventType.ERROR:
            if event.role is not None or event.content is not None:
                raise InvalidAgentEventError("error must not include role/content.")
            if not event.metadata.get("message"):
                raise InvalidAgentEventError("error requires metadata['message'].")

    @abstractmethod
    async def _execute(
        self,
        thread: ThreadContext,
        config: ExecutionConfig,
    ) -> AsyncIterator[AgentEvent]: ...
