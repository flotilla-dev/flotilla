from langchain_openai import ChatOpenAI

from config.settings import Settings
from config.config_models import LLMConfig


class LLMProvider:
    """
    Provider class that is used to look up the current LLM instance that is configured to be used by this application
    """
    def get_llm(self, config: LLMConfig | None = None) -> ChatOpenAI:
        """Factory method to create a LLM instance from the LLMConfig object.  If the config is not provided then the default config is used"""
        if (config is None):
            settings = Settings()
            config = settings.get_llm_config()
        
        return ChatOpenAI(
            model = config.model_name,
            api_key=config.api_key,
            temperature=config.temperature
        )

