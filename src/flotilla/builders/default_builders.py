from langgraph.types import Checkpointer
from langgraph.checkpoint.memory import InMemorySaver

from dependency_injector import providers

from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.tools.tool_registry import ToolRegistry
from flotilla.agents.agent_registry import BusinessAgentRegistry
from flotilla.selectors.keyword_agent_selector import KeywordAgentSelector
from flotilla.tools.base_tool_provider import BaseToolProvider

from typing import Any, List, Optional


def memory_checkpointer_builder(*, container: FlotillaContainer, config: Optional[dict]) -> Checkpointer:
    """
    Creates an InMemorySaver Checkpointer implementation.  Useful during testing
    """
    return InMemorySaver()


    
def keyword_agent_selector_builder(*, container: FlotillaContainer, config: Optional[dict]) -> KeywordAgentSelector:
    """
    Builder function for the KeywordAgentSelector that is configured from the yaml file.  If min_confidence is not available a default value of 0.7 is used
    
    :param container: The DI Container
    :type container: containers.DeclarativeContainer
    :param config: The ConfigurationOption that encapsulates the dict from flotilla.yml
    :type config: providers.ConfigurationOption
    :return: A fully configured and ready to use KeywordAgentSelector
    :rtype: KeywordAgentSelector
    """
    # TODO is this check still necessary?
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