from typing import Any, Optional, Dict, List
from enum import Enum
from pydantic import BaseModel, Field


class ResponseStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    FAILURE = "failure"


class ErrorResponse(BaseModel):
    error_code: str = Field(..., description="Short stable error identifier")
    error_details: Any = Field(..., description="Raw or structured error payload")


class BusinessAgentResponse(BaseModel):
    """
    Standardized response returned by all BusinessAgent.execute() implementations.
    Ensures orchestration can reason uniformly across agents.
    """

    # Required metadata
    status: ResponseStatus = Field(..., description="The status of the agent call")
    agent_name: str = Field(..., description="Name of the agent producing this response")
    query: str = Field(..., description="The original user query that triggered the agent")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0–1.0"
    )
    message: Optional[str] = Field(None, description="Human-readable summary message")

    # Structured agent-specific result payload
    data: Dict[str, Any] = Field(default_factory=dict)

    # Orchestration hints (multi-step workflows)
    actions: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="List of next actions the orchestration agent may take"
    )

    # Error list (optional)
    errors: Optional[List[ErrorResponse]] = Field(
        None,
        description="List of errors that occurred"
    )
