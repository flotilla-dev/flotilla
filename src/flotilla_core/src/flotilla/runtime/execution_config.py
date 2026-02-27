from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class ExecutionConfig(BaseModel):
    """
    Stable execution configuration for a conversation thread.
    """

    thread_id: str = Field(
        ..., description="Unique identifier for the conversation thread"
    )

    recursion_limit: int = Field(
        default=10, description="Maximum depth of recursive tool/LLM execution"
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )
