
from agents.agent_selector import AgentSelector
from agents.selectors.keyword_agent_selector import KeywordAgentSelector
#from agents.selectors.llm_agent_selector import LLMAgentSelector
from agents.selectors.vector_agent_selector import VectorAgentSelector
from config.config_models import AgentSelectorConfig, VectorAgentSelectorConfig, KeywordAgentSelectorConfig, LLMAgentSelectorConfig


class AgentSelectorFactory:

    def create_agent_selector(config:AgentSelectorConfig) -> AgentSelector:
        if isinstance(config, VectorAgentSelectorConfig):
            return VectorAgentSelector(config)
        elif isinstance(config, KeywordAgentSelectorConfig):
            return KeywordAgentSelector(config)
        elif isinstance(config, LLMAgentSelectorConfig):
            return None
        else:
            raise TypeError(f"Cannot create AgentSelector instance for unkknow config {type(config)}")
