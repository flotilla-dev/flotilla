from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum
from .content_part import ContentPart
from flotilla.agents.agent_event import AgentEvent, AgentEventType
from flotilla.runtime.phase_context import PhaseContext
from flotilla.thread.thread_entries import ThreadEntry


class RuntimeEventType(str, Enum):
    START = "START"
    PART = "PART"
    COMPLETE = "COMPLETE"
    SUSPEND = "SUSPEND"
    ERROR = "ERROR"


class RuntimeEvent(BaseModel):
    type: RuntimeEventType = Field(..., description="Status of the response to the request")
    phase_id: str = Field(..., description="The unique ID of the execution phase")
    thread_id: str = Field(..., description="The id of the current ThreadContext")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this event was emitted",
    )
    correlation_id: Optional[str] = Field(
        default=None,
        description="User supplied ID that allows for correlation to a Phase",
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Trace ID that allows for tracing execution via telemetry",
    )
    resume_token: Optional[str] = Field(
        default=None,
        description="Token string that is used to resume execution of a thread",
    )
    content: Optional[List[ContentPart]] = Field(
        default=None,
        description="List of ContentPart objects that are core of the request to the Flotilla",
    )

    class Config:
        frozen = True
        extra = "forbid"


class RuntimeEventFactory:
    @staticmethod
    def create_runtime_event(
        agent_event: AgentEvent,
        phase_context: PhaseContext,
        resume_token: Optional[str] = None,
    ) -> RuntimeEvent:
        if agent_event.type == AgentEventType.MESSAGE_START:
            return RuntimeEvent(
                type=RuntimeEventType.START,
                phase_id=phase_context.phase_id,
                thread_id=phase_context.thread_id,
                correlation_id=phase_context.correlation_id,
                trace_id=phase_context.trace_id,
            )
        elif agent_event.type == AgentEventType.MESSAGE_CHUNK:
            return RuntimeEvent(
                type=RuntimeEventType.PART,
                phase_id=phase_context.phase_id,
                thread_id=phase_context.thread_id,
                correlation_id=phase_context.correlation_id,
                trace_id=phase_context.trace_id,
                content=agent_event.content,
            )
        elif agent_event.type == AgentEventType.MESSAGE_FINAL:
            return RuntimeEvent(
                type=RuntimeEventType.COMPLETE,
                phase_id=phase_context.phase_id,
                thread_id=phase_context.thread_id,
                correlation_id=phase_context.correlation_id,
                trace_id=phase_context.trace_id,
                content=agent_event.content,
            )
        elif agent_event.type == AgentEventType.SUSPEND:
            return RuntimeEvent(
                type=RuntimeEventType.SUSPEND,
                phase_id=phase_context.phase_id,
                thread_id=phase_context.thread_id,
                correlation_id=phase_context.correlation_id,
                trace_id=phase_context.trace_id,
                content=agent_event.content,
                resume_token=resume_token,
            )
        elif agent_event.type == AgentEventType.ERROR:
            return RuntimeEvent(
                type=RuntimeEventType.ERROR,
                phase_id=phase_context.phase_id,
                thread_id=phase_context.thread_id,
                correlation_id=phase_context.correlation_id,
                trace_id=phase_context.trace_id,
                content=agent_event.content,
            )

        else:
            # shouldn't get here
            return None
