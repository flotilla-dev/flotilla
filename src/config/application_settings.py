from pydantic import BaseModel, Field
from typing import Dict, Any


class ApplicationSettings(BaseModel):
    """
    Application-level configuration loaded from YAML files
    (agents.yml, tools.yml, feature_flags.yml) and merged
    with environment-specific overrides.
    """

    agent_configs: Dict[str, Any] = Field(default_factory=dict)
    tool_configs: Dict[str, Any] = Field(default_factory=dict)
    feature_flags: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"  # allow additional arbitrary app config
