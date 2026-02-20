from pydantic import BaseModel
from typing import Any, Optional
from flotilla.core.runtime_event_type import RuntimeEventType


class RuntimeEvent(BaseModel):
    type: RuntimeEventType
    payload: Any
    agent_name: Optional[str] = None

    class Config:
        frozen = True
        extra = "forbid"
