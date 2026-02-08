from pydantic import BaseModel, Field
from typing import Optional, Any, Dict

class AgentInput(BaseModel):
    query:str = Field(..., description="The user supplied query to execute")
    user_id:Optional[str] = Field(default=None, description="The id of the current user")
    thread_id:Optional[str] = Field(default=None, description="The id of the current conversation")
    metadata:Optional[Dict[str, Any]] = Field(default_factory=dict, description="A set of additional metadata passed to the execution context")

    class Config:
        frozen = True
        extra = "forbid"