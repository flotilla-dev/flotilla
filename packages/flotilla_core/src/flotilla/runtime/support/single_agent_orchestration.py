from flotilla.runtime.orchestration_strategy import OrchestrationStrategy
from flotilla.runtime.phase_context import PhaseContext
from flotilla.thread.thread_context import ThreadContext
from flotilla.agents.flotilla_agent import FlotillaAgent
from flotilla.telemetry.telemetry_service import TelemetryService
from flotilla.telemetry.telemetry_event import TelemetryEvent
from flotilla.telemetry.telemetry_types import TelemetryType, TelemetryComponent
from flotilla.agents.agent_event import AgentEvent
from flotilla.runtime.content_part import TextPart
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)


class SingleAgentOrchestration(OrchestrationStrategy):

    def __init__(self, agent: FlotillaAgent, telemetry: TelemetryService):
        self._agent = agent
        self._telemetry = telemetry

    async def execute(self, thread_context: ThreadContext, phase_context: PhaseContext):
        logger.info(
            "Start single-agent orchestration for agent '%s' thread '%s' phase '%s'",
            self._agent.agent_name,
            phase_context.thread_id,
            phase_context.phase_id,
        )
        self._telemetry.emit(
            TelemetryEvent.info(
                type=TelemetryType.AGENT_RUN_STARTED,
                component=TelemetryComponent.AGENT,
                message=f"Starting execution of Agent {self._agent.agent_name}",
            )
        )
        try:

            async for event in self._agent.run(
                thread_context=thread_context,
                phase_context=phase_context,
                input_parts=[],
            ):
                logger.debug(
                    "Single-agent orchestration yielded event %s for agent '%s'",
                    event.type,
                    self._agent.agent_name,
                )
                yield event

            logger.info(
                "Complete single-agent orchestration for agent '%s' thread '%s' phase '%s'",
                self._agent.agent_name,
                phase_context.thread_id,
                phase_context.phase_id,
            )
            self._telemetry.emit(
                TelemetryEvent.info(
                    type=TelemetryType.AGENT_RUN_COMPLETED,
                    component=TelemetryComponent.AGENT,
                    message=f"Completed execution of Agent {self._agent.agent_name}",
                )
            )
        except Exception as e:
            logger.exception(
                "Single-agent orchestration failed for agent '%s' thread '%s' phase '%s'",
                self._agent.agent_name,
                phase_context.thread_id,
                phase_context.phase_id,
            )
            self._telemetry.emit(
                TelemetryEvent.error(
                    type=TelemetryType.AGENT_RUN_FAILED,
                    component=TelemetryComponent.AGENT,
                    message=f"Error while executing Agent {self._agent.agent_name}",
                    exception=e,
                )
            )
            yield AgentEvent.error(
                entry_id=thread_context.last_entry.entry_id,
                content=[TextPart(f"Agent {self._agent.agent_name} execution failed.")],
            )
