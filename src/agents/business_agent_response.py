from typing import Any, Optional, Dict, List
from enum import Enum
from pydantic import BaseModel, Field


class ResponseStatus(Enum):
    # ----- Agent success/final states -----
    SUCCESS = "success"                       # Agent fully completed task

    # ----- Agent intermediate / non-error workflow states -----
    NEEDS_INPUT = "needs_input"               # Agent requires clarification from the user
    NEEDS_TOOL = "needs_tool"                 # Agent must call a tool or external step
    PARTIAL_SUCCESS = "partial_success"       # Agent completed part of the task
    NOT_APPLICABLE = "not_applicable"         # Agent acknowledges query doesn't belong here

    # ----- Soft agent errors returned *within valid JSON* -----
    ERROR = "error"                           # Agent reports a domain-level failure

    # ----- System-level / infrastructure errors (outside JSON) -----
    LLM_OUTPUT_ERROR = "llm_output_error"     # Invalid JSON, schema mismatch
    LLM_CALL_FAILED = "llm_call_failed"       # API error, timeout, model failure
    APP_MISCONFIGURED = "app_misconfigured"   # Registry/config/env problems
    INTERNAL_ERROR = "internal_error"         # Uncaught exceptions in your code


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

    reasong: Optional[str] = Field(None, description="Description of how the LLM made its decision")

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
