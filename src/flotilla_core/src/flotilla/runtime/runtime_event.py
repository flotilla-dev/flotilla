from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum
from .content_part import ContentPart


class RuntimeEventType(str, Enum):
    START = "START"
    PART = "PART"
    COMPLETE = "COMPLETE"
    SUSPEND = "SUSPEND"
    ERROR = "ERROR"


class RuntimeEvent(BaseModel):
    type: RuntimeEventType = Field(
        ..., description="Status of the response to the request"
    )
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
