from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional


class Severity(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class TelemetryEvent(BaseModel):
    event_type: str = Field(
        ..., description="Canonical identifier describing what occurred."
    )
    component: str = Field(..., description="Name of the emitting component")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO-8601 timestamp indicating when the event was emitted.",
    )
    severity: Severity = Field(
        default=Severity.INFO,
        description="Reflects observability classification, not execution outcome.",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured identifiers for correlation and trace alignment. All fields are optional and may be null. MUST NOT contain `ContentPart`, secrets, or raw tool payloads.",
    )
    attributes: Dict[str, Any] = Field(
        ...,
        description="Flat JSON-safe key-value map. Used for durations, counters, flags, configuration identifiers, and state indicators. MUST NOT contain sensitive information",
    )

    class Config:
        frozen = True
        extra = "forbid"

    @classmethod
    def debug(cls, *, type: str, component: str, message: str) -> TelemetryEvent:
        return cls(
            event_type=type,
            component=component,
            severity=Severity.DEBUG,
            attributes={"message": message},
        )

    @classmethod
    def info(cls, *, type: str, component: str, message: str) -> TelemetryEvent:
        return cls(
            event_type=type,
            component=component,
            severity=Severity.INFO,
            attributes={"message": message},
        )

    @classmethod
    def warn(
        cls, *, type: str, component: str, message: str, exception: Optional[Exception]
    ) -> TelemetryEvent:
        attributes = {"message": message}

        if exception:
            attributes["exception"] = str(exception)

        return cls(
            event_type=type,
            component=component,
            severity=Severity.WARNING,
            attributes=attributes,
        )

    @classmethod
    def error(
        cls, *, type: str, component: str, message: str, exception: Exception
    ) -> TelemetryEvent:
        return cls(
            event_type=type,
            component=component,
            severity=Severity.ERROR,
            attributes={"message": message, "exception": str(exception)},
        )
