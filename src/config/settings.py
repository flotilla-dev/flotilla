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


    def get_llm_config(self) -> LLMConfig:
        """Creates a LLM Config"""
        return self._get_openai_llm_config()
    
    
    def _get_openai_llm_config(self) -> LLMConfig:
        """Creates an OpenAIConfig"""
        return OpenAIConfig(
            api_key=self.LLM__API_KEY,
            model_name=self.LLM__MODEL,
            temperature=self.LLM__TEMPERATURE
        )
        
    
    def get_tool_registry_config(self) -> ToolRegistryConfig:
        """Creates a Tool Registry Config"""
        return ToolRegistryConfig(
            tool_packages = self.TOOL_REGISTRY__PACKAGES,
            tool_recursive = self.TOOL_REGISTRY__RECURISVE
        )
        
    
    def get_agent_registry_config(self) -> AgentRegistryConfig:
        """Creates an Agent Registry Config"""
        return AgentRegistryConfig(
            agent_packages = self.AGENT_REGISTRY__PACKAGES,
            agent_recursive = self.AGENT_REGISTRY__RECURSIVE,
            llm_config = self.get_llm_config()
        )
        
    
    def get_orchestration_config(self) -> OrchestrationConfig:
        """Creates the config for the Orchestration agent"""
        return OrchestrationConfig(
            llm_config=self.get_llm_config(),
            log_level=self.LOG__LEVEL,
            client=self.get_client_config(),
        )

    def get_client_config(self) -> ClientConfig:
        """Creates a Client Config object from the internal settings"""
        return ClientConfig(
            client_id = "test_1",
            client_name = "Test",
            llm_config = self.get_llm_config()
        )
        
