from __future__ import annotations

from typing import Any, Dict, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field, ConfigDict, field_validator
from abc import ABC, abstractmethod
from enum import Enum
import json
import re


class ContentPartType(str, Enum):
    TEXT = "text"
    STRUCTURED = "structured"
    FILE = "file"


# ============================================================
# Base
# ============================================================


class ContentPartBase(BaseModel, ABC):
    """
    Base value object for user, agent, and runtime message content.

    Content parts are embedded in RuntimeRequest, RuntimeResponse,
    RuntimeEvent, and durable ThreadEntry records. Subclasses define how a
    specific payload type is validated and serialized so content can move
    safely between API boundaries, thread storage, and agent execution.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=True,  # ensures enums serialize as strings if used elsewhere
    )

    type: str = Field(..., description="The type of ContentPart, must be a value from ContentPartType")
    id: Optional[str] = Field(
        default=None, description="An optional id value that can be used to identify the intent of the content"
    )

    @abstractmethod
    def serialize(self) -> str: ...

    @classmethod
    @abstractmethod
    def deserialize(cls, payload: str) -> ContentPart: ...


# ============================================================
# TextPart
# ============================================================


class TextPart(ContentPartBase):
    type: Literal[ContentPartType.TEXT] = ContentPartType.TEXT
    text: str = Field(..., description="The text value of the ContentPart")
    mime_type: str = Field(default="text/plain", description="The MIME type of the TextPart, defaults to text/plain")

    @field_validator("mime_type")
    @classmethod
    def validate_mime(cls, v):
        if not re.match(r"^text/.*", v):
            raise ValueError("mime_type must start with text/")
        return v

    def serialize(self) -> str:
        return json.dumps(
            self.model_dump(exclude_none=True, mode="json"),
            sort_keys=True,
        )

    @classmethod
    def deserialize(cls, payload: str) -> TextPart:
        data = json.loads(payload)
        return cls(**data)


# ============================================================
# StructuredPart
# ============================================================


class StructuredPart(ContentPartBase):
    type: Literal[ContentPartType.STRUCTURED] = ContentPartType.STRUCTURED
    mime_type: str = Field(
        default="application/json", description="The MIME type of the StructuredPart, defaults to application/json"
    )
    data: Any = Field(..., description="The data of the StrucutredPart")

    @field_validator("mime_type")
    @classmethod
    def validate_mime(cls, v):
        if not re.match(r"^application/.*", v):
            raise ValueError("mime_type should start with application/")
        return v

    def serialize(self) -> str:
        return json.dumps(
            self.model_dump(exclude_none=True, mode="json"),
            sort_keys=True,
        )

    @classmethod
    def deserialize(cls, payload: str) -> StructuredPart:
        data = json.loads(payload)
        return cls(**data)


# ============================================================
# FilePart
# ============================================================


class FilePart(ContentPartBase):
    type: Literal[ContentPartType.FILE] = ContentPartType.FILE

    url: str = Field(description="Externally accessible URL to file content.")

    mime_type: str = Field(description="MIME type describing the file format.")

    bytes: Optional[int] = Field(default=None, ge=0, description="Optional file size in bytes.")

    sha256: Optional[str] = Field(default=None, description="Optional SHA-256 hex digest of file content.")

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.fullmatch(r"[a-fA-F0-9]{64}", v):
            raise ValueError("sha256 must be a 64-character hexadecimal string")
        return v

    def serialize(self) -> str:
        return json.dumps(
            self.model_dump(exclude_none=True, mode="json"),
            sort_keys=True,
        )

    @classmethod
    def deserialize(cls, payload: str) -> "FilePart":
        data = json.loads(payload)
        return cls(**data)


# ============================================================
# Discriminated Union
# ============================================================

ContentPart = Annotated[
    Union[TextPart, StructuredPart, FilePart],
    Field(discriminator="type"),
]


# ============================================================
# Static Factory
# ============================================================


class ContentPartFactory:
    @staticmethod
    def deserialize_part(payload: str) -> ContentPart:
        try:
            data = json.loads(payload)
        except Exception as e:
            raise ValueError("Invalid JSON payload") from e

        part_type = data.get("type")
        if not part_type:
            raise ValueError("Missing 'type' field")

        match part_type:
            case "text":
                return TextPart.deserialize(payload)
            case "structured":
                return StructuredPart.deserialize(payload)
            case "file":
                return FilePart.deserialize(payload)
            case _:
                raise ValueError(f"Unknown type: {part_type}")
