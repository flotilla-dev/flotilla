from typing import List, Optional
from abc import ABC
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from flotilla.runtime.content_part import ContentPart
from flotilla.runtime.message_role import MessageRole
from flotilla.agents.agent_event import AgentEvent, AgentEventType
from flotilla.runtime.phase_context import PhaseContext


class ThreadEntry(BaseModel, ABC):
    def __init__(self, **data):
        if self.__class__ is ThreadEntry:
            raise TypeError("ThreadEntry is abstract and cannot be instantiated directly")
        super().__init__(**data)

    thread_id: str = Field(..., description="The unique id of the conversation thread")

    phase_id: str = Field(
        ...,
        description="The ID of the execution phase to which this ThreadEntry belongs",
    )

    entry_id: Optional[str] = Field(
        default=None,
        description="The unique id of an individual entry assigned by ConversationStore",
    )

    previous_entry_id: Optional[str] = Field(
        default=None,
        description="The ID of the entry previous to this one in the ThreadContext",
    )

    timestamp: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp assigned by ConversationStore",
    )

    content: List[ContentPart] = Field(
        min_length=1,
        description="The content that defines the state change of the Thread",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )


class UserInput(ThreadEntry):
    role: MessageRole = MessageRole.USER
    user_id: str = Field(..., description="The ID of the user that generated the UserInput")


class AgentOutput(ThreadEntry):
    role: MessageRole = MessageRole.AGENT
    agent_id: str = Field(..., description="The ID of the agent that generated the output")


class SuspendEntry(ThreadEntry):
    role: MessageRole = MessageRole.SYSTEM
    agent_id: str = Field(..., description="The ID of the agent that casued the suspend")


class ResumeEntry(ThreadEntry):
    role: MessageRole = MessageRole.USER
    user_id: str = Field(..., description="The ID of the user that generated the ResumeEntry")


class ClosedEntry(ThreadEntry):
    role: MessageRole = MessageRole.USER
    user_id: str = Field(..., description="The ID of the user that closed the Thread")


class ErrorEntry(ThreadEntry):
    role: MessageRole = MessageRole.SYSTEM
    agent_id: str = Field(..., description="The ID of the agent that generated the error")


class ThreadEntryFactory:
    """
    Static factor for converting an AgentEvent into valid ThreadEntry objects.  Only terminal events are converted to a ThreadEntry.  If None is returned then the event does NOT map to a ThreadEntry
    """

    @staticmethod
    def create_entry(agent_event: AgentEvent, phase_context: PhaseContext) -> Optional[ThreadEntry]:
        if agent_event.type == AgentEventType.MESSAGE_FINAL:
            # create AgentOutput
            return AgentOutput(
                thread_id=phase_context.thread_id,
                phase_id=phase_context.phase_id,
                previous_entry_id=agent_event.previous_entry_id,
                content=agent_event.content,
                agent_id=agent_event.agent_id,
            )
        elif agent_event.type == AgentEventType.ERROR:
            return ErrorEntry(
                thread_id=phase_context.thread_id,
                phase_id=phase_context.phase_id,
                previous_entry_id=agent_event.previous_entry_id,
                content=agent_event.content,
                agent_id=agent_event.agent_id,
            )
        elif agent_event.type == AgentEventType.SUSPEND:
            return SuspendEntry(
                thread_id=phase_context.thread_id,
                phase_id=phase_context.phase_id,
                previous_entry_id=agent_event.previous_entry_id,
                content=agent_event.content,
                agent_id=agent_event.agent_id,
            )
        else:
            return None
