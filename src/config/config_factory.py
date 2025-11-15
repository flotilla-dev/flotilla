"""
Configuration Factory for creating config models from settings
"""
from typing import Dict, Any
from config.config_models import (
    LLMConfig,
    OpenAIConfig,
    AzureOpenAIConfig,
    ToolRegistryConfig,
    AgentRegistryConfig,
    OrchestrationConfig,
    ClientConfig
)
from config.settings import Settings, LLMType


class ConfigFactory:
    """Factory class for creating configuration models from settings"""

    @staticmethod
    def create_llm_config(settings:Settings) -> LLMConfig:
        """
        Creates the appropriate LLM Configuratoin based on LLM type
        
        Args:
            settings: Application settings instance
        
        Returns:
            LLMCOnfig: The LLMConfig to pass to the LLMFactory
        """
        if settings.LLM__TYPE == LLMType.OPENAI:
            return ConfigFactory._create_openai_config(settings)
        elif settings.LLM__TYPE == LLMType.AZURE_OPENAI:
            return ConfigFactory._create_azure_openai_config(settings)
        else:
            raise ValueError("Unsupported LLM type: {settings.LLM__TYPE}")

    @staticmethod
    def _create_openai_config(settings:Settings) -> OpenAIConfig:
        """Creates an OpenAIConfig"""
        return OpenAIConfig(
            api_key=settings.LLM__API_KEY,
            model_name=settings.LLM__MODEL,
            temperature=settings.LLM__TEMPERATURE
        )
    
    @staticmethod
    def _create_azure_openai_config(settings:Settings) -> AzureOpenAIConfig:
        pass

    @staticmethod
    def create_tool_registry_config(settings:Settings) -> ToolRegistryConfig:
        """Creates a Tool Registry Config"""
        return ToolRegistryConfig(
            tool_packages = settings.TOOL_REGISTRY__PACKAGES,
            tool_recursive = settings.TOOL_REGISTRY__RECURISVE,
            tool_discovery = settings.TOOL_REGISTRY__ENABLE_DISCOVERY
        )
    
    @staticmethod
    def create_agent_registry_config(settings:Settings) -> AgentRegistryConfig:
        """Creates an Agent Registry Config"""
        return AgentRegistryConfig(
            agent_packages = settings.AGENT_REGISTRY__PACKAGES,
            agent_recursive = settings.AGENT_REGISTRY__RECURSIVE,
            agent_discovery = settings.AGENT_REGISTRY__ENABLE_DISCOVERY,
            llm_config = ConfigFactory.create_llm_config(settings)
        )
    
    def create_client_config(settings:Settings) -> ClientConfig:
        """Creates a Client Config object from the internal settings"""
        return ClientConfig(
            client_id = "test_1",
            client_name = "Test"        )
    
    def create_orchestration_config(settings:Settings) -> OrchestrationConfig:
        """Creates the config for the Orchestration agent"""
        return OrchestrationConfig(
            llm_config=ConfigFactory.create_llm_config(settings),
            log_level=settings.LOG__LEVEL,
            client=ConfigFactory.create_client_config(settings),
            tool_registry_config=ConfigFactory.create_tool_registry_config(settings),
            agent_registry_config=ConfigFactory.create_agent_registry_config(settings)
        )
