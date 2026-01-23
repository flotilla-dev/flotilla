from pydantic import BaseModel, Field
from typing import Optional

class ExecutionConfig(BaseModel):
    thread_id: Optional[str] = Field(default=None, description="The id of the converation")
    recursion_limit: int = Field(default=10, description="The depth of recursion allowed by the LLM")
    trace_id: Optional[str] = Field(default=None, description="The unqiue id for a single execution")
    stream: bool = False

    class Config:
        frozen = True  # immutable by default
