from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, model_validator
from flotilla.core.content_part import ContentPart


# -----------------------
# Enums
# -----------------------
class AgentEventType(str, Enum):
    MESSAGE_START = "message_start"
    MESSAGE_CHUNK = "message_chunk"
    MESSAGE_FINAL = "message_final"
    SUSPEND = "suspend"
    ERROR = "error"


class MessageRole(str, Enum):
    AGENT = "agent"
    USER = "user"
    SYSTEM = "system"


# -----------------------
# AgentEvent
# -----------------------
class AgentEvent(BaseModel):
    type: AgentEventType

    role: Optional[MessageRole] = None
    message_id: Optional[str] = None

    content_text: Optional[str] = None
    content: Optional[List[ContentPart]] = None

    metadata: Optional[Dict[str, Any]] = None

    reason: Optional[str] = None

    message: Optional[str] = None
    recoverable: Optional[bool] = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_semantics(self) -> "AgentEvent":
        t = self.type

        if t is AgentEventType.MESSAGE_START:
            if self.role is None or self.message_id is None:
                raise ValueError("message_start requires role and message_id")
            if self.content_text is not None or self.content is not None:
                raise ValueError(
                    "message_start must not include content_text or content"
                )

        elif t is AgentEventType.MESSAGE_CHUNK:
            if self.role is None or self.message_id is None:
                raise ValueError("message_chunk requires role and message_id")
            if self.content_text is None:
                raise ValueError("message_chunk requires content_text")
            if self.content is not None:
                raise ValueError("message_chunk must not contain structured content")

        elif t is AgentEventType.MESSAGE_FINAL:
            if self.role is None or self.message_id is None:
                raise ValueError("message_final requires role and message_id")
            if not self.content:
                raise ValueError("message_final requires non-empty content list")
            if self.content_text is not None:
                raise ValueError("message_final must not use content_text")

        elif t is AgentEventType.SUSPEND:
            if not self.reason:
                raise ValueError("suspend requires reason")
            if self.role or self.message_id or self.content_text or self.content:
                raise ValueError("suspend must not include message fields")

        elif t is AgentEventType.ERROR:
            if not self.message:
                raise ValueError("error requires message")
            if self.recoverable is None:
                raise ValueError("error requires recoverable")
            if self.role or self.message_id or self.content_text or self.content:
                raise ValueError("error must not include message fields")

        return self

    # -----------------------
    # Factory methods (Enum-based)
    # -----------------------
    @classmethod
    def message_start(cls, role: MessageRole, message_id: str) -> AgentEvent:
        return cls(
            type=AgentEventType.MESSAGE_START,
            role=role,
            message_id=message_id,
        )

    @classmethod
    def message_chunk(cls, role: MessageRole, message_id: str, text: str) -> AgentEvent:
        return cls(
            type=AgentEventType.MESSAGE_CHUNK,
            role=role,
            message_id=message_id,
            content_text=text,
        )

    @classmethod
    def message_final(
        cls,
        role: MessageRole,
        message_id: str,
        content: List[ContentPart],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentEvent:
        return cls(
            type=AgentEventType.MESSAGE_FINAL,
            role=role,
            message_id=message_id,
            content=content,
            metadata=metadata,
        )

    @classmethod
    def suspend(cls, reason: str) -> AgentEvent:
        return cls(
            type=AgentEventType.SUSPEND,
            reason=reason,
        )

    @classmethod
    def error(cls, message: str, recoverable: bool) -> AgentEvent:
        return cls(
            type=AgentEventType.ERROR,
            message=message,
            recoverable=recoverable,
        )
