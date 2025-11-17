from pydantic import BaseModel
from typing import Dict, Any


class ApplicationSettings(BaseModel):
    """
    Application-level configuration owned by the application.
    Contains domain configuration and per-agent config.
    """

    # Developer-defined config per agent
    agent_configs: Dict[str, Dict[str, Any]] = {}

    # Optional domain/business flags
    feature_flags: Dict[str, bool] = {}

    class Config:
        extra = "allow"  # allow additional arbitrary app config
