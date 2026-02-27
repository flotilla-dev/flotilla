from flotilla.runtime.orchestration_strategy import OrchestrationStrategy
from flotilla.runtime.execution_config import ExecutionConfig
from flotilla.thread.thread_context import ThreadContext
from flotilla.agents.flotilla_agent import FlotillaAgent
from flotilla.telemetry.telemetry_policy import TelemetryPolicy
from flotilla.telemetry.telemetry_event import TelemetryEvent
from flotilla.telemetry.telemetry_types import TelemeryType, TelemetryComponent
from flotilla.agents.agent_event import AgentEvent
from flotilla.runtime.content_part import TextPart


class SingleAgentOrchestration(OrchestrationStrategy):

    def __init__(self, agent: FlotillaAgent, telemetry: TelemetryPolicy):
        self._agent = agent
        self._telemetry = telemetry

    async def execute(
        self, thread_context: ThreadContext, execution_config: ExecutionConfig
    ):
        self._telemetry.emit(
            TelemetryEvent.info(
                type=TelemeryType.AGENT_RUN_START,
                component="SingleAgentOrchestration",
                message=f"Starting execution of Agent {self._agent.agent_name}",
            )
        )
        try:

            async for event in self._agent.run(
                thread_context=thread_context,
                execution_config=execution_config,
                input_parts=[],
            ):
                yield event

            self._telemetry.emit(
                TelemetryEvent.info(
                    type=TelemeryType.AGENT_RUN_COMPLETE,
                    component="SingleAgentOrchestration",
                    message=f"Completed execution of Agent {self._agent.agent_name}",
                )
            )
        except Exception as e:
            self._telemetry.emit(
                TelemetryEvent.error(
                    type=TelemeryType.AGENT_RUN_ERROR,
                    component="SingleAgentOrchestration",
                    message=f"Error while executing Agent {self._agent.agent_name}",
                    exception=e,
                )
            )
            yield AgentEvent.error(
                entry_id=thread_context.last_entry.entry_id,
                content=[TextPart(f"Agent {self._agent.agent_name} execution failed.")],
            )
