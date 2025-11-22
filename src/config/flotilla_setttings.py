from pydantic_settings import BaseSettings
from pydantic import Field
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
    LLM__API_KEY: str = Field(..., description="API Key for the LLM used by the application.  Should not be set in a config file")
    LLM__MODEL: str = Field(..., description="The type of the model to be used by the LLM")
    LLM__TEMPERATURE: float = Field(..., description="The temperature value to use with LLM")
    LLM__TYPE: LLMType = Field(..., description="The type of LLM to use")

    # Logging
    LOG__LEVEL: str = Field(default="INFO", description="The Log Level to use with the application")

    # Tool registry discovery
    TOOL_REGISTRY__PACKAGES: List[str] = Field(..., description="The list of packages to search for Tools")
    TOOL_REGISTRY__RECURISVE: bool = Field(default=True, description="If tool discovery should recursively search for folders")
    TOOL_REGISTRY__ENABLE_DISCOVERY: bool = Field(default=True, description="Controls if the Tool Regisry should automatically search for tools in the packages list")

    # Agent registry discovery
    AGENT_REGISTRY__PACKAGES: List[str] = Field(..., description="The list of packages to search for Agents") 
    AGENT_REGISTRY__RECURSIVE: bool = Field(default=True, description="If Agent discovery should recursively search for folders")
    AGENT_REGISTRY__ENABLE_DISCOVERY: bool = Field(default=True, description="Controls if the Agent Regisry should automatically search for agents in the packages list")

    class ConfigDict:
        env_file = ".env"
