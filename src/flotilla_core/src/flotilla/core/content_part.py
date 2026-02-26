from __future__ import annotations

from typing import Any, Dict, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field, HttpUrl, ConfigDict, field_validator
from enum import Enum
import re


class ContentPartType(str, Enum):
    TEXT = "text"
    JSON = "json"
    FILE = "file"


# ============================================================
# Base
# ============================================================


class ContentPartBase(BaseModel):
    """
    Base class for all ContentPart variants.
    """

    model_config = ConfigDict(
        extra="forbid",  # no open-ended metadata
        frozen=True,  # immutable once created
        validate_assignment=False,
    )

    type: ContentPartType
    id: Optional[str] = Field(
        default=None,
        description="Optional identifier unique within a single message_final.",
    )


# ============================================================
# TextPart
# ============================================================


class TextPart(ContentPartBase):
    type: Literal[ContentPartType.TEXT] = ContentPartType.TEXT
    text: str = Field(..., description="Plain text content.")


# ============================================================
# JsonPart
# ============================================================


class JsonPart(ContentPartBase):
    type: Literal[ContentPartType.JSON] = ContentPartType.JSON
    data: Dict[str, Any] = Field(..., description="JSON-serializable structured data.")


# ============================================================
# FilePart
# ============================================================


class FilePart(ContentPartBase):
    type: Literal[ContentPartType.FILE] = ContentPartType.FILE

    url: HttpUrl = Field(description="Externally accessible URL to file content.")

    mime_type: str = Field(description="MIME type describing the file format.")

    bytes: Optional[int] = Field(
        default=None, ge=0, description="Optional file size in bytes."
    )

    sha256: Optional[str] = Field(
        default=None, description="Optional SHA-256 hex digest of file content."
    )

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.fullmatch(r"[a-fA-F0-9]{64}", v):
            raise ValueError("sha256 must be a 64-character hexadecimal string")
        return v


# ============================================================
# Discriminated Union
# ============================================================

ContentPart = Annotated[
    Union[TextPart, JsonPart, FilePart, ReasoningPart, ConfidencePart],
    Field(discriminator="type"),
]
