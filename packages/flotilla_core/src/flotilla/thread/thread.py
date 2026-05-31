from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ThreadAttribute(BaseModel):
    """
    Creation-time key/value metadata attached to a thread.
    """

    key: str = Field(..., min_length=1, description="Attribute key unique within a thread.")
    value: Any = Field(..., description="JSON-serializable attribute value.")
    created_at: Optional[datetime] = Field(default=None, description="Store-assigned attribute creation timestamp.")

    @field_validator("value")
    @classmethod
    def validate_json_serializable(cls, value: Any) -> Any:
        try:
            json.dumps(value)
        except TypeError as exc:
            raise ValueError("ThreadAttribute.value must be JSON-serializable") from exc
        return value

    model_config = ConfigDict(frozen=True, extra="forbid")


class Thread(BaseModel):
    """
    Durable thread identity and metadata record.
    """

    thread_id: str = Field(..., description="Store-assigned thread identifier.")
    title: str = Field(..., min_length=1, description="Human-readable thread title.")
    created_at: datetime = Field(..., description="Store-assigned thread creation timestamp.")
    created_by: Optional[str] = Field(default=None, description="Application-defined creator identifier.")

    model_config = ConfigDict(frozen=True, extra="forbid")


class CreateThreadRequest(BaseModel):
    """
    Request to create a durable thread and its immutable creation-time attributes.
    """

    title: str = Field(..., min_length=1, description="Human-readable thread title.")
    created_by: Optional[str] = Field(default=None, description="Application-defined creator identifier.")
    attributes: list[ThreadAttribute] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_attributes(self):
        keys = [attribute.key for attribute in self.attributes]
        if len(keys) != len(set(keys)):
            raise ValueError("ThreadAttribute keys must be unique")
        if any(attribute.created_at is not None for attribute in self.attributes):
            raise ValueError("Client-supplied ThreadAttribute.created_at is not allowed")
        return self

    model_config = ConfigDict(frozen=True, extra="forbid")
