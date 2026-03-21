from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any


class PhaseContext(BaseModel):
    """
    Immutable per-phase execution metadata and optional agent-specific configuration.
    """

    thread_id: str = Field(
        ..., description="Unique identifier for the conversation thread"
    )

    phase_id: str = Field(..., description="Unique ID for the execution phase")

    user_id: str = Field(..., description="ID of the current user")

    correlation_id: Optional[str] = Field(
        default=None,
        description="User supplied ID that is used to correlate Flotilla execution IDs to user's environment",
    )

    trace_id: Optional[str] = Field(
        default=None,
        description="Trace ID that allows for tracing execution via telemetry",
    )

    agent_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional collection of Agent specifc execution configuration",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )
