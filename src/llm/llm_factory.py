from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import BaseChatOpenAI
from langchain_openai.chat_models.azure import AzureChatOpenAI


from config.settings import Settings
from config.config_models import LLMConfig, OpenAIConfig, AzureOpenAIConfig
from utils.logger import get_logger

logger = get_logger(__name__)

class LLMFactory:
    """
    Provider class that is used to look up the current LLM instance that is configured to be used by this application
    """

    def __init__(self):
        """Initailize the LLMFactory to have a Dict of concrete LLMConfig instances"""
        self.builders = {
            OpenAIConfig.__name__: self._build_openai,
            AzureOpenAIConfig.__name__: self._build_azure,
        }


    def get_llm(self, config: LLMConfig | None = None) -> BaseChatOpenAI:
        """Factory method to create a LLM instance from the LLMConfig object.  If the config is not provided then the default config is used"""
        if config is None:
            logger.debug("LLMConfig instance is None, use default from Settings")
            settings = Settings()
            config = settings.get_llm_config()

        config_name = config.__class__.__name__
        logger.debug(f"Look up builder function for config {config_name}")
        
        func = self.builders.get(config_name)
        if func is None:
            raise ValueError(f"Cannot create LLM for unknown config {config_name}")
        
        logger.info(f"Create LLM instance for config {config}")
        return func(config)
            
    
    def _build_openai(self, config:OpenAIConfig) -> ChatOpenAI:
        return ChatOpenAI(
            model = config.model_name,
            api_key=config.api_key,
            temperature=config.temperature,
            max_completion_tokens=config.max_tokens
        )
    
    def _build_azure(self, config:AzureOpenAIConfig) -> AzureChatOpenAI:
        return AzureChatOpenAI(
            azure_endpoint=config.endpoint,
            api_key=config.api_key,
            api_version=config.api_version,
            deployment_name=config.deployment_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
