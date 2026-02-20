from pydantic import BaseModel, Field
from typing import Any, Optional
from enum import Enum


class ResultStatus(str, Enum):
    SUCCESS = "success"
    AWAITING_INPUT = "awaiting_input"
    INTERRUPTED = "interrupted"
    ERROR = "error"


class RuntimeResult(BaseModel):
    status: ResultStatus = Field(..., description="Terminal execution status")

    class Config:
        frozen = True
        extra = "forbid"
