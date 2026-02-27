from typing import Union, List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from flotilla.runtime.content_part import ContentPart
from flotilla.runtime.message_role import MessageRole


class ThreadEntry(BaseModel):
    thread_id: str = Field(..., description="The unique id of the conversation thread")

    entry_id: Optional[str] = Field(
        default=None,
        description="The unique id of an individual entry assigned by ConversationStore",
    )

    timestamp: Optional[datetime] = Field(
        default=None, description="UTC timestamp assigned by ConversationStore"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional JSON-serializable metadata"
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )


class UserInput(ThreadEntry):
    role: MessageRole = MessageRole.USER
    user_id: Optional[str] = None
    content: List[ContentPart] = Field(min_length=1)


class AgentOutput(ThreadEntry):
    role: MessageRole = MessageRole.AGENT
    agent_id: Optional[str] = None
    content: List[ContentPart] = Field(min_length=1)


class SuspendEntry(ThreadEntry):
    role: MessageRole = MessageRole.SYSTEM
    content: List[ContentPart] = Field(min_length=1)


class ResumeEntry(ThreadEntry):
    role: MessageRole = MessageRole.USER
    user_id: Optional[str] = None
    content: List[ContentPart] = Field(min_length=1)


class ClosedEntry(ThreadEntry):
    role: MessageRole = MessageRole.USER
    user_id: Optional[str] = None


class ErrorEntry(ThreadEntry):
    role: MessageRole = MessageRole.SYSTEM
    message: str = Field(..., description="Human-readable error message")
    recoverable: bool = Field(
        ..., description="Indicates whether execution may be retried"
    )
    error_type: Optional[str] = Field(
        default=None,
        description="Optional machine-readable error classification",
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional structured error metadata",
    )
