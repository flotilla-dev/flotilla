from pydantic import BaseModel, Field
from typing import Any, Optional
from enum import Enum
from flotilla.core.execution_checkpoint import ExecutionCheckpoint


class ResultStatus(str, Enum):
    SUCCESS = "success"
    AWAITING_INPUT = "awaiting_input"
    INTERRUPTED = "interrupted"
    ERROR = "error"



class RuntimeResult(BaseModel):
    status: ResultStatus = Field(
        ...,
        description="Terminal execution status"
    )

    output: Optional[Any] = Field(
        default=None,
        description="Projected output for the caller (often agent data)"
    )

    agent_name: Optional[str] = Field(
        default=None,
        description="Name of the agent responsible for the terminal result"
    )

    checkpoint: Optional[ExecutionCheckpoint] = Field(
        default=None,
        description="Checkpoint for resuming execution if suspended"
    )

    metadata: dict = Field(
        default_factory=dict,
        description="Runtime-level metadata (timing, tracing, diagnostics)"
    )

    class Config:
        frozen = True
        extra = "forbid"
