from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from flotilla.runtime.content_part import (
    ContentPart,
    TextPart,
)


# -----------------------
# Enums
# -----------------------
class AgentEventType(str, Enum):
    MESSAGE_START = "message_start"
    MESSAGE_CHUNK = "message_chunk"
    MESSAGE_FINAL = "message_final"
    SUSPEND = "suspend"
    ERROR = "error"


# -----------------------
# AgentEvent
# -----------------------
class AgentEvent(BaseModel):
    type: AgentEventType = Field(..., description="The type of Event from the AgentEventType Enum")
    previous_entry_id: str = Field(..., description="The id of the ThreadEntry that started this execution phase")
    agent_id: str = Field(..., description="The ID of the Agnet that emitted this event")
    content: List[ContentPart] = Field(
        default_factory=list,
        description="The list of ContentPart objects that are emitted by the Agent",
    )
    execution_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata that is used to capture data about execution of the Agent",
    )
    is_terminal: bool = Field(..., description="Dictates if the AgentEvent type is terminal or not")

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_event(self):
        if self.type == AgentEventType.MESSAGE_START:
            if self.content:
                raise ValueError("message_start must not contain content")

        elif self.type == AgentEventType.MESSAGE_CHUNK:
            if len(self.content) != 1:
                raise ValueError("message_chunk must contain exactly one ContentPart")
            if not isinstance(self.content[0], TextPart):
                raise ValueError("message_chunk must contain a TextPart")

        elif self.type == AgentEventType.MESSAGE_FINAL:
            if not self.content:
                raise ValueError("message_final must contain content")

        return self

    # -----------------------
    # Factory methods (Enum-based)
    # -----------------------
    @classmethod
    def message_start(cls, *, entry_id: str, agent_id: str) -> AgentEvent:
        return cls(type=AgentEventType.MESSAGE_START, previous_entry_id=entry_id, agent_id=agent_id, is_terminal=False)

    @classmethod
    def message_chunk(
        cls,
        *,
        entry_id: str,
        agent_id: str,
        text: str,
    ) -> AgentEvent:
        return cls(
            type=AgentEventType.MESSAGE_CHUNK,
            previous_entry_id=entry_id,
            agent_id=agent_id,
            content=[TextPart(text=text)],
            is_terminal=False,
        )

    @classmethod
    def message_final(
        cls,
        *,
        entry_id: str,
        agent_id: str,
        content: List[ContentPart],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentEvent:
        return cls(
            type=AgentEventType.MESSAGE_FINAL,
            previous_entry_id=entry_id,
            agent_id=agent_id,
            content=content,
            execution_metadata=metadata,
            is_terminal=True,
        )

    @classmethod
    def suspend(
        cls,
        *,
        entry_id: str,
        agent_id: str,
        content: List[ContentPart],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentEvent:
        return cls(
            type=AgentEventType.SUSPEND,
            previous_entry_id=entry_id,
            agent_id=agent_id,
            content=content,
            execution_metadata=metadata,
            is_terminal=True,
        )

    @classmethod
    def error(
        cls,
        *,
        entry_id: str,
        agent_id: str,
        content: List[ContentPart],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentEvent:
        return cls(
            type=AgentEventType.ERROR,
            previous_entry_id=entry_id,
            agent_id=agent_id,
            content=content,
            execution_metadata=metadata,
            is_terminal=True,
        )
