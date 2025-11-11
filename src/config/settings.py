from pydantic_settings import BaseSettings
from typing import List
from config.config_models import LLMConfig, ToolRegistryConfig, AgentRegistryConfig, OrchestrationConfig, ClientConfig, OpenAIConfig, AzureOpenAIConfig
from enum import Enum


class LLMType(Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


class Settings(BaseSettings):
    """Application Settings"""

    llm_api_key: str = "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"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: str = "0"
    llm_type:LLMType = LLMType.OPENAI

    enable_tracing: bool = False
    max_retries: int = 3
    log_level:str = "INFO"
    retry_delay: float = 1.0
    tool_packages: List[str] = ["tools"]
    tool_recursive:bool = True

    agent_packages: List[str] = ["agents.business_logic"]
    agent_recursive:bool = True


    class ConfigDict:
        env_file = ".env"


    def get_llm_config(self) -> LLMConfig:
        """Creates a LLM Config"""
        return self._get_openai_llm_config()
    
    
    def _get_openai_llm_config(self) -> LLMConfig:
        """Creates an OpenAIConfig"""
        return OpenAIConfig(
            api_key=self.llm_api_key,
            model_name=self.llm_model,
            temperature=self.llm_temperature
        )
        
    
    def get_tool_registry_config(self) -> ToolRegistryConfig:
        """Creates a Tool Registry Config"""
        return ToolRegistryConfig(
            tool_packages = self.tool_packages,
            tool_recursive = self.tool_recursive
        )
        
    
    def get_agent_registry_config(self) -> AgentRegistryConfig:
        """Creates an Agent Registry Config"""
        return AgentRegistryConfig(
            agent_packages = self.agent_packages,
            agent_recursive = self.agent_recursive,
            llm_config = self.get_llm_config()
        )
        
    
    def get_orchestration_config(self) -> OrchestrationConfig:
        """Creates the config for the Orchestration agent"""
        return OrchestrationConfig(
            llm_config=self.get_llm_config(),
            enable_tracing=self.enable_tracing,
            log_level=self.log_level,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            client=self.get_client_config(),
        )

    def get_client_config(self) -> ClientConfig:
        """Creates a Client Config object from the internal settings"""
        return ClientConfig(
            client_id = "test_1",
            client_name = "Test",
            llm_config = self.get_llm_config()
        )
        
