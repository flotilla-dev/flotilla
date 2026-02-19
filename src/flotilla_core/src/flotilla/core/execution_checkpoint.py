from pydantic import BaseModel, Field
from typing import Any, Dict

class ExecutionCheckpoint(BaseModel):
    execution_id: str = Field(
        ...,
        description="Stable identifier for a single execution instance"
    )
    payload: Dict[str, Any] = Field(
        ...,
        description="Opaque runtime-owned execution snapshot"
    )
    version: int = Field(
        default=1,
        description="Checkpoint schema version"
    )

    class Config:
        frozen = True
        extra = "forbid"
