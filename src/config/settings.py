from pydantic_settings import BaseSettings
from typing import List
from config.config_models import LLMConfig, ToolRegistryConfig, AgentRegistryConfig, OrchestrationConfig, ClientConfig, OpenAIConfig, AzureOpenAIConfig
from enum import Enum


class LLMType(Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


class Settings(BaseSettings):
    """Application Settings"""

    # General LLM configuration Items
    LLM__API_KEY: str = "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"
    LLM__MODEL: str = "gpt-4o-mini"
    LLM__TEMPERATURE: str = "0"
    LLM__TYPE:LLMType = LLMType.OPENAI

    # Azure specific configuration items

    # logging configuration
    LOG__LEVEL:str = "INFO"

    # Tool Registry configuration
    TOOL_REGISTRY__PACKAGES: List[str] = ["tools"]
    TOOL_REGISTRY__RECURISVE:bool = True
    TOOL_REGISTRY__ENABLE_DISCOVERY:bool = True


    # Agent Registry cofiguration
    AGENT_REGISTRY__PACKAGES: List[str] = ["agents.business_logic"]
    AGENT_REGISTRY__RECURSIVE:bool = True
    AGENT_REGISTRY__ENABLE_DISCOVERY:bool = True

    # Orchestration configuration


    class ConfigDict:
        env_file = ".env"
  
