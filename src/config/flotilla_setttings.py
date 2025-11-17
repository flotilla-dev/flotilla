from pydantic_settings import BaseSettings
from typing import List
from enum import Enum


class LLMType(Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


class FlotillaSettings(BaseSettings):
    """
    Framework-level settings used by the agent framework.
    Loaded from environment variables, .env, Azure AppConfig, etc.
    """

    # LLM configuration
    LLM__API_KEY: str = "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"
    LLM__MODEL: str = "gpt-4o-mini"
    LLM__TEMPERATURE: str = "0"
    LLM__TYPE: LLMType = LLMType.OPENAI

    # Logging
    LOG__LEVEL: str = "INFO"

    # Tool registry discovery
    TOOL_REGISTRY__PACKAGES: List[str] = ["tools"]
    TOOL_REGISTRY__RECURISVE: bool = True
    TOOL_REGISTRY__ENABLE_DISCOVERY: bool = True

    # Agent registry discovery
    AGENT_REGISTRY__PACKAGES: List[str] = ["agents.business_logic"]
    AGENT_REGISTRY__RECURSIVE: bool = True
    AGENT_REGISTRY__ENABLE_DISCOVERY: bool = True

    class ConfigDict:
        env_file = ".env"
