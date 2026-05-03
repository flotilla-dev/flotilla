from typing import List, Optional, Dict, Any, Union, Annotated, Literal
from enum import Enum
from abc import ABC
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator, TypeAdapter
from flotilla.runtime.content_part import ContentPart
from flotilla.agents.agent_event import AgentEvent, AgentEventType
from flotilla.runtime.phase_context import PhaseContext


class ThreadEntryType(str, Enum):
    USER_INPUT = "user"
    AGENT_OUTPUT = "agent"
    SUSPEND_ENTRY = "suspend"
    RESUME_ENTRY = "resume"
    CLOSED_ENTRY = "closed"
    ERROR_ENTRY = "error"


class ActorType(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class ThreadEntryBase(BaseModel, ABC):
    """
    Base durable record for every runtime thread state transition.

    FlotillaRuntime appends concrete ThreadEntry variants to represent user
    input, agent output, suspend, resume, close, and error transitions. Stores
    assign identity, order, and timestamp fields during append. ThreadContext
    later derives execution status from the ordered entries.
    """

    type: ThreadEntryType = Field(..., description="The type of ThreadEntry class")

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

    entry_order: Optional[int] = Field(
        default=None,
        description="The numerical order of the entry within the thread log that ia assigned during append() operation",
    )

    timestamp: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp assigned by ConversationStore",
    )

    actor_type: ActorType = Field(..., description="The type of the actor that generated this ThreadEntry")

    actor_id: str = Field(
        ...,
        description="The ID of the actor that casued this state transition.  Refer to actor_type to identify the type of actor",
    )

    content: List[ContentPart] = Field(
        min_length=1,
        description="The content that defines the state change of the Thread",
    )

    def serialize(self) -> Dict[str, Any]:
        return self.model_dump(mode="python", exclude_none=True)

    @model_validator(mode="after")
    def validate_actor_consistency(self):
        if self.type in {
            ThreadEntryType.USER_INPUT,
            ThreadEntryType.RESUME_ENTRY,
            ThreadEntryType.CLOSED_ENTRY,
        }:
            if self.actor_type != ActorType.USER:
                raise ValueError("Start entries must have actor_type=USER")

        elif self.type in {
            ThreadEntryType.AGENT_OUTPUT,
            ThreadEntryType.SUSPEND_ENTRY,
            ThreadEntryType.ERROR_ENTRY,
        }:
            if self.actor_type not in {ActorType.AGENT, ActorType.SYSTEM}:
                raise ValueError("Terminal entries must have actor_type=AGENT or SYSTEM")

        return self

    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=True)


class UserInput(ThreadEntryBase):
    type: Literal[ThreadEntryType.USER_INPUT] = ThreadEntryType.USER_INPUT
    actor_type: Literal[ActorType.USER] = ActorType.USER


class AgentOutput(ThreadEntryBase):
    type: Literal[ThreadEntryType.AGENT_OUTPUT] = ThreadEntryType.AGENT_OUTPUT
    actor_type: Literal[ActorType.AGENT] = ActorType.AGENT


class SuspendEntry(ThreadEntryBase):
    type: Literal[ThreadEntryType.SUSPEND_ENTRY] = ThreadEntryType.SUSPEND_ENTRY
    actor_type: Literal[ActorType.SYSTEM] = ActorType.SYSTEM


class ResumeEntry(ThreadEntryBase):
    type: Literal[ThreadEntryType.RESUME_ENTRY] = ThreadEntryType.RESUME_ENTRY
    actor_type: Literal[ActorType.USER] = ActorType.USER


class ClosedEntry(ThreadEntryBase):
    type: Literal[ThreadEntryType.CLOSED_ENTRY] = ThreadEntryType.CLOSED_ENTRY
    actor_type: Literal[ActorType.USER] = ActorType.USER


class ErrorEntry(ThreadEntryBase):
    type: Literal[ThreadEntryType.ERROR_ENTRY] = ThreadEntryType.ERROR_ENTRY
    actor_type: Literal[ActorType.SYSTEM] = ActorType.SYSTEM


ThreadEntry = Annotated[
    Union[UserInput, AgentOutput, SuspendEntry, ResumeEntry, ErrorEntry, ClosedEntry], Field(discriminator="type")
]


class ThreadEntryFactory:

    _adapter = TypeAdapter(ThreadEntry)

    @staticmethod
    def deserialize_entry(data: Dict[str, Any]) -> ThreadEntry:
        return ThreadEntryFactory._adapter.validate_python(data)

    @staticmethod
    def create_entry_from_agent_event(agent_event: AgentEvent, phase_context: PhaseContext) -> Optional[ThreadEntry]:
        """
        Static factory method for converting an AgentEvent into valid ThreadEntry objects.  Only terminal events are converted to a ThreadEntry.  If None is returned then the event does NOT map to a ThreadEntry
        """
        if agent_event.type == AgentEventType.MESSAGE_FINAL:
            # create AgentOutput
            return AgentOutput(
                thread_id=phase_context.thread_id,
                phase_id=phase_context.phase_id,
                previous_entry_id=agent_event.previous_entry_id,
                content=agent_event.content,
                actor_id=agent_event.agent_id,
            )
        elif agent_event.type == AgentEventType.ERROR:
            return ErrorEntry(
                thread_id=phase_context.thread_id,
                phase_id=phase_context.phase_id,
                previous_entry_id=agent_event.previous_entry_id,
                content=agent_event.content,
                actor_id=agent_event.agent_id,
                actor_type=ActorType.AGENT,
            )
        elif agent_event.type == AgentEventType.SUSPEND:
            return SuspendEntry(
                thread_id=phase_context.thread_id,
                phase_id=phase_context.phase_id,
                previous_entry_id=agent_event.previous_entry_id,
                content=agent_event.content,
                actor_id=agent_event.agent_id,
            )
        else:
            return None
