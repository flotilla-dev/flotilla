from langgraph.types import Checkpointer
from langgraph.checkpoint.memory import InMemorySaver

from dependency_injector import containers, providers

from flotilla.tools.tool_registry import ToolRegistry
from flotilla.agents.agent_registry import BusinessAgentRegistry
from flotilla.agents.selectors.keyword_agent_selector import KeywordAgentSelector
from flotilla.agents.selectors.vector_agent_selector import VectorAgentSelector
from flotilla.tools.base_tool_provider import BaseToolProvider

from typing import Any, List, Optional


def memory_checkpointer_builder(*, container: containers.DeclarativeContainer, config: Optional[dict]) -> Checkpointer:
    """
    Creates an InMemorySaver Checkpointer implementation.  Useful during testing
    """
    return InMemorySaver()


def default_tool_registry_builder(*, container: containers.DeclarativeContainer, config:Optional[dict], tool_provider_names:List[BaseToolProvider] ) -> ToolRegistry:
    tool_providers: List[BaseToolProvider] = []

    for attr_name in tool_provider_names:
        if not hasattr(container, attr_name):
            raise ValueError(
                f"Tool provider '{attr_name}' is not wired on the container"
            )

        provider = getattr(container, attr_name)

        # If it's a DI provider, calling it returns the instance.
        instance = provider() if callable(provider) else provider

        if not isinstance(instance, BaseToolProvider):
            raise TypeError(
                f"Container attribute '{attr_name}' did not resolve to a BaseToolProvider "
                f"(got {type(instance).__name__})"
            )

        tool_providers.append(instance)

    return ToolRegistry(tool_providers=tool_providers)
    
def keyword_agent_selector_builder(*, container: containers.DeclarativeContainer, config: Optional[dict]) -> KeywordAgentSelector:
    """
    Builder function for the KeywordAgentSelector that is configured from the yaml file.  If min_confidence is not available a default value of 0.7 is used
    
    :param container: The DI Container
    :type container: containers.DeclarativeContainer
    :param config: The ConfigurationOption that encapsulates the dict from flotilla.yml
    :type config: providers.ConfigurationOption
    :return: A fully configured and ready to use KeywordAgentSelector
    :rtype: KeywordAgentSelector
    """
    if callable(config):
        raw = config()
    else:
        raw = config or {}
    min_confidence = float(raw.get("min_confidence", 0.7))

    return KeywordAgentSelector(
        min_confidence=min_confidence,
    )

'''
def vector_agent_selector_builder(*, container: containers.DeclarativeContainer, config: providers.ConfigurationOption | None) -> KeywordAgentSelector:
    return VectorAgentSelector()
'''

'''
def default_agent_registry_buidler(*, container: containers.DeclarativeContainer, config: providers.ConfigurationOption | None) -> BusinessAgentRegistry:
    return BusinessAgentRegistry()

'''