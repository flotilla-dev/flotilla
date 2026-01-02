import pytest
from unittest.mock import MagicMock, patch
from typing import Any

from flotilla.agents.wiring.agent_contributor import AgentContributor
from flotilla.agents.wiring.agent_context import AgentContext
from flotilla.flotilla_configuration_error import FlotillaConfigurationError
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.flotilla_settings import FlotillaSettings
from langgraph.types import Checkpointer
from langchain.chat_models import BaseChatModel

@pytest.fixture
def container(minimal_settings):
    container = FlotillaContainer(settings=minimal_settings)

    # stub methods we want to observe
    container.wire_from_config = MagicMock()
    container.get = MagicMock()

    return container


def test_agent_contributor_wires_all_agents(mock_checkpointer, mock_llm, agent_factory):
    # create the contirbutor and config to test
    contributor = AgentContributor()
    context = AgentContext()

    # create the test settings
    settings = FlotillaSettings(
        {
            "agents": {
                "weather": {
                    "builder": "weather_agent_builder",
                    "llm": {"provider": "mock"},
                },
                "calculator": {
                    "builder": "calculator_agent_builder",
                    "llm": {"provider": "mock"},
                },
            },
            "llm": {
                "mock": {
                    "builder": "mock_llm_builder",
                    "model": "test-model",
                    "temperature": 0.0,
                }
            },
        }
    )

    # create contaier from the settings
    container = FlotillaContainer(settings=settings)

    # create simple builder function to return mock llm and register to the container
    def mock_llm_builder(container:FlotillaContainer, config:dict) -> Any:
        return mock_llm
    
    # create the mock agents and their buidler functions 
    weather_agent = agent_factory(agent_id="weather_agent", capabilities=[], dependencies=[])
    def weather_agent_builder(container:FlotillaContainer, config:dict, llm:BaseChatModel, checkpointer:Checkpointer) -> Any:
        return weather_agent
    
    calculator_agent = agent_factory(agent_id="calculator_agent", capabilities=[], dependencies=[])
    def calculator_agent_builder(container:FlotillaContainer, config:dict, llm:BaseChatModel, checkpointer:Checkpointer) -> Any:
        return calculator_agent
    
    # register the builders
    container.register_builder("mock_llm_builder", mock_llm_builder)
    container.register_builder("weather_agent_builder", weather_agent_builder)
    container.register_builder("calculator_agent_builder", calculator_agent_builder)

    # place the checkpointer on the container so it is available to the contributor
    setattr(container.di, "checkpointer", mock_checkpointer)

    # mock the LLM Factory to return the  mock_llm
    contributor.contribute(container, context)

    # make sure the name of the agents matches the name at the section head in YAML
    assert container.exists("weather")
    assert container.exists("calculator")
    assert not container.exists("weather_agent")
    assert not container.exists("calculator_agent")


def test_agent_contributor_raises_if_checkpointer_missing(container):
    # create the contirbutor and config to test
    contributor = AgentContributor()
    context = AgentContext()

    # create the test settings
    settings = FlotillaSettings(
        {
            "agents": {
                "weather": {
                    "builder": "weather_agent_builder",
                    "llm": {"provider": "mock"},
                }
            }})
    container = FlotillaContainer(settings=settings)

    with pytest.raises(FlotillaConfigurationError):
        contributor.contribute(container, context)

def test_agent_contributor_no_agents_is_noop(container):
    contributor = AgentContributor()
    context = AgentContext()

    container = FlotillaContainer(FlotillaSettings({}))
    contributor.contribute(container, context)

    assert context.agent_names == []

def test_agent_contributor_validate_noop(container):
    contributor = AgentContributor()
    context = AgentContext()

    contributor.validate(container, context)
