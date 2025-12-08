"""
Configuration Factory for creating config models from settings
"""
from config.config_models import (
    LLMConfig,
    OpenAIConfig,
    AzureOpenAIConfig,
    ToolRegistryConfig,
    AgentRegistryConfig,
    OrchestrationConfig,
    ClientConfig,
    BusinessAgentConfg,
    AgentSelectorConfig,
    VectorAgentSelectorConfig,
    LLMAgentSelectorConfig,
    KeywordAgentSelectorConfig,
    ToolConfig
)
from config.settings import Settings, ApplicationSettings, FlotillaSettings
from config.flotilla_setttings import LLMType
from langgraph.types import Checkpointer
from langgraph.checkpoint.memory import InMemorySaver

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
        if settings.flotilla.LLM__TYPE == LLMType.OPENAI:
            return ConfigFactory._create_openai_config(settings)
        elif settings.flotilla.LLM__TYPE == LLMType.AZURE_OPENAI:
            return ConfigFactory._create_azure_openai_config(settings)
        else:
            raise ValueError("Unsupported LLM type: {settings.LLM__TYPE}")

    @staticmethod
    def _create_openai_config(settings:Settings) -> OpenAIConfig:
        """Creates an OpenAIConfig"""
        return OpenAIConfig(
            api_key=settings.flotilla.LLM__API_KEY,
            model_name=settings.flotilla.LLM__MODEL,
            temperature=settings.flotilla.LLM__TEMPERATURE,
            feature_flags=settings.application.feature_flags
        )
    
    @staticmethod
    def _create_azure_openai_config(settings:Settings) -> AzureOpenAIConfig:
        pass

    @staticmethod
    def create_tool_registry_config(settings:Settings) -> ToolRegistryConfig:
        """Creates a Tool Registry Config"""
        return ToolRegistryConfig(
            tool_packages = settings.flotilla.TOOL_REGISTRY__PACKAGES,
            tool_recursive = settings.flotilla.TOOL_REGISTRY__RECURISVE,
            tool_discovery = settings.flotilla.TOOL_REGISTRY__ENABLE_DISCOVERY,
            feature_flags=settings.application.feature_flags,
            settings= settings
        )
    
    @staticmethod
    def create_agent_registry_config(settings:Settings) -> AgentRegistryConfig:
        """Creates an Agent Registry Config"""
        return AgentRegistryConfig(
            agent_packages = settings.flotilla.AGENT_REGISTRY__PACKAGES,
            agent_recursive = settings.flotilla.AGENT_REGISTRY__RECURSIVE,
            agent_discovery = settings.flotilla.AGENT_REGISTRY__ENABLE_DISCOVERY,
            llm_config = ConfigFactory.create_llm_config(settings),
            feature_flags=settings.application.feature_flags,
            agent_selector_config=ConfigFactory.create_agent_selector_config(settings),
            settings=settings
        )
    
    @staticmethod
    def create_client_config(settings:Settings) -> ClientConfig:
        """Creates a Client Config object from the internal settings"""
        return ClientConfig(
            client_id = "test_1",
            client_name = "Test"        )
    
    @staticmethod
    def create_orchestration_config(settings:Settings) -> OrchestrationConfig:
        """Creates the config for the Orchestration agent"""
        return OrchestrationConfig(
            llm_config=ConfigFactory.create_llm_config(settings),
            log_level=settings.flotilla.LOG__LEVEL,
            client=ConfigFactory.create_client_config(settings),
            tool_registry_config=ConfigFactory.create_tool_registry_config(settings),
            agent_registry_config=ConfigFactory.create_agent_registry_config(settings),
            feature_flags=settings.application.feature_flags
        )
    
    @staticmethod
    def create_business_agent_config(agent_id:str, settings:Settings) -> BusinessAgentConfg:
        """Creates a BusinessAgentConfig for a specific BusinessAgent from the Settings"""
        agent_config = settings.application.agent_configs.get(agent_id, {})
        llm_config = ConfigFactory._override_llm_config(ConfigFactory.create_llm_config(settings), agent_config)
        return BusinessAgentConfg(
            agent_configuration=agent_config,
            llm_config=llm_config,
            feature_flags=settings.application.feature_flags,
            checkpointer=ConfigFactory._create_checkpointer(settings)
        )
    
    @staticmethod
    def _create_checkpointer(settings:Settings) -> Checkpointer:
        """Creates a Checkpointer instance based on the passed Settings"""
        return InMemorySaver()
    
    @staticmethod
    def _override_llm_config(llm_config:LLMConfig, config:dict) -> LLMConfig:
        """Uses the parameters from the Agent config to override the standard LLMConfig"""
        llm_config.temperature = config.get("llm", {}).get("temperature", llm_config.temperature)
        llm_config.max_tokens = config.get("llm", {}).get("max_tokens", llm_config.max_tokens)
        if isinstance(llm_config, OpenAIConfig):
            llm_config = ConfigFactory._override_openai_llm_config(llm_config=llm_config, config=config)
        return llm_config
    
    @staticmethod
    def _override_openai_llm_config(llm_config:OpenAIConfig, config:dict) -> OpenAIConfig:
        """Overrides the values on the OpenAIConfig oblect from the agent"""
        llm_config.model_name = config.get("llm", {}).get("model", llm_config.model_name)
        return llm_config
    
    @staticmethod
    def create_tool_config(tool_id:str, settings:Settings) -> ToolConfig:
        return ToolConfig(
            tool_configuration=settings.application.tool_configs.get(tool_id, {}),
            feature_flags=settings.application.feature_flags
        )
    

    def create_agent_selector_config(settings: Settings) -> AgentSelectorConfig:
        if settings.flotilla.AGENT_SELECTOR__TYPE == "vector":
            return ConfigFactory._create_vector_agent_select_config(settings)
        elif settings.flotilla.AGENT_SELECTOR__TYPE == "keyword":
            return ConfigFactory._create_keyword_agent_selector_config(settings)
        elif settings.flotilla.AGENT_SELECTOR__TYPE == "llm":
            return ConfigFactory._create_llm_agent_selector_config(settings)
        else:
            raise TypeError(f"Cannot create AgentSelector for unknown type {settings.flotilla.AGENT_SELECTOR__TYPE}")

    def _create_vector_agent_select_config(settings:Settings) -> VectorAgentSelectorConfig:
        return VectorAgentSelectorConfig(
            min_confidence=settings.flotilla.AGENT_SELECTOR__MIN_CONFIDENCE,
            embedding_model=settings.flotilla.AGENT_SELECTOR__EMBEDDING_MODEL,
            settings=settings
        )

    def _create_keyword_agent_selector_config(settings:Settings) -> KeywordAgentSelectorConfig:
        return KeywordAgentSelectorConfig(
            min_confidence=settings.flotilla.AGENT_SELECTOR__MIN_CONFIDENCE,
            settings=settings
        )

    def _create_llm_agent_selector_config(settings:Settings) -> LLMAgentSelectorConfig:
        return LLMAgentSelectorConfig(
            min_confidence=settings.flotilla.AGENT_SELECTOR__MIN_CONFIDENCE,
            llm_config=ConfigFactory.create_llm_config(settings)
        )