from collections.abc import AsyncIterator
from typing import Optional
from flotilla.core.flotilla_runtime import FlotillaRuntime
from flotilla.core.agent_input import AgentInput
from flotilla.agents.base_business_agent import BaseBusinessAgent
from flotilla.agents.business_agent_response import (
    BusinessAgentResponse,
    ResponseStatus,
)
from flotilla.core.execution_checkpoint import ExecutionCheckpoint
from flotilla.core.execution_config import ExecutionConfig
from flotilla.core.runtime_event import RuntimeEvent
from flotilla.core.runtime_event_type import RuntimeEventType
from flotilla.core.runtime_result import RuntimeResult, ResultStatus

from flotilla.utils.logger import get_logger

logger = get_logger(__name__)


class SingleAgentRuntime(FlotillaRuntime):
    """
    Runtime that executes a single BaseBusinessAgent instance.
    """

    def __init__(self, *, agent: BaseBusinessAgent):
        self._agent = agent
        agent

    async def stream(
        self,
        *,
        agent_input: AgentInput,
        execution_config: ExecutionConfig,
        checkpoint: Optional[ExecutionCheckpoint] = None,
    ) -> AsyncIterator[RuntimeEvent]:

        # START
        yield RuntimeEvent(
            type=RuntimeEventType.START,
            payload={"agent": self._agent.get_name()},
            agent_name=self._agent.get_name(),
        )

        try:
            response: BusinessAgentResponse = self._agent.run(
                agent_input=agent_input,
                config=execution_config,
            )

            # Suspension cases
            if response.status in {
                ResponseStatus.NEEDS_INPUT,
                ResponseStatus.NEEDS_TOOL,
            }:
                yield RuntimeEvent(
                    type=RuntimeEventType.AWAIT_INPUT,
                    payload={
                        "message": response.message,
                        "actions": getattr(response, "actions", None),
                        "data": response.data,
                    },
                    agent_name=response.agent_name,
                )
                return

            # Success / terminal
            if response.status == ResponseStatus.SUCCESS:
                yield RuntimeEvent(
                    type=RuntimeEventType.COMPLETE,
                    payload=response.data,
                    agent_name=response.agent_name,
                )
                return

            # Soft or hard errors
            yield RuntimeEvent(
                type=RuntimeEventType.ERROR,
                payload={
                    "message": response.message,
                    "errors": response.errors,
                },
                agent_name=response.agent_name,
            )

        except Exception as exc:
            logger.error(
                "Error streaming results from Agent call, emitting error event",
                exc_info=True,
            )
            yield RuntimeEvent(
                type=RuntimeEventType.ERROR,
                payload={"error": str(exc)},
                agent_name=self._agent.get_name(),
            )

    async def run(
        self,
        *,
        agent_input: AgentInput,
        execution_config: ExecutionConfig,
        checkpoint: Optional[ExecutionCheckpoint] = None,
    ) -> BusinessAgentResponse:

        last_event: RuntimeEvent | None = None

        async for event in self.stream(
            agent_input=agent_input,
            execution_config=execution_config,
        ):
            last_event = event

            if event.type == RuntimeEventType.AWAIT_INPUT:
                return RuntimeResult(
                    status=ResultStatus.AWAITING_INPUT,
                    output=event.payload,
                    agent_name=event.agent_name,
                )

        if last_event is None:
            raise RuntimeError("Runtime produced no events")

        if last_event.type == RuntimeEventType.COMPLETE:
            return RuntimeResult(
                status=ResultStatus.SUCCESS,
                output=last_event.payload,
                agent_name=last_event.agent_name,
            )

        return RuntimeResult(
            status=ResultStatus.ERROR,
            output=last_event.payload,
            agent_name=last_event.agent_name,
        )
