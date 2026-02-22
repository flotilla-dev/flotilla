from __future__ import annotations

from typing import Any, Dict, Literal, Optional, Union
from pydantic import BaseModel, Field, HttpUrl, ConfigDict, field_validator
import re


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

    type: str
    id: Optional[str] = Field(
        default=None,
        description="Optional identifier unique within a single message_final.",
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.strip():
            raise ValueError("id must not be empty or whitespace")
        return v


# ============================================================
# TextPart
# ============================================================


class TextPart(ContentPartBase):
    type: Literal["text"]
    text: str = Field(description="Plain text content.")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if v is None:
            raise ValueError("text must not be None")
        return v


# ============================================================
# JsonPart
# ============================================================


class JsonPart(ContentPartBase):
    type: Literal["json"]
    data: Dict[str, Any] = Field(description="JSON-serializable structured data.")

    @field_validator("data")
    @classmethod
    def validate_json_serializable(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        # Pydantic ensures dict structure; we just ensure no non-serializable obvious types
        # If needed, this can be tightened further.
        return v


# ============================================================
# FilePart
# ============================================================


class FilePart(ContentPartBase):
    type: Literal["file"]

    url: HttpUrl = Field(description="Externally accessible URL to file content.")

    mime_type: str = Field(description="MIME type describing the file format.")

    bytes: Optional[int] = Field(
        default=None, ge=0, description="Optional file size in bytes."
    )

    sha256: Optional[str] = Field(
        default=None, description="Optional SHA-256 hex digest of file content."
    )

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        if not v or "/" not in v:
            raise ValueError(
                "mime_type must be a valid MIME type (e.g., application/pdf)"
            )
        return v

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

ContentPart = Union[
    TextPart,
    JsonPart,
    FilePart,
]
