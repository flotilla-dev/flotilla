from pydantic import BaseModel
from typing import Any, Optional
from flotilla.core.execution_checkpoint import ExecutionCheckpoint
from flotilla.core.runtime_event_type import RuntimeEventType

class RuntimeEvent(BaseModel):
    type: RuntimeEventType
    payload: Any
    agent_name: Optional[str] = None
    checkpoint: Optional[ExecutionCheckpoint] = None

    class Config:
        frozen = True
        extra = "forbid"
