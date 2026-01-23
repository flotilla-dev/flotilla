import pytest
from unittest.mock import MagicMock

from flotilla.agents.agent_registry import BusinessAgentRegistry
from flotilla.core.errors import FlotillaConfigurationError
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.agents.builders.agent_registry_builder import agent_registry_builder

@pytest.fixture
def container():
    container = MagicMock(spec=FlotillaContainer)
    return container

def test_agent_registry_builder_happy_path(
    container,
    agent_factory,
    mock_agent_selector,
    mock_tool_registry,
):
    agent_names = ["weather", "calculator"]

    weather_agent = agent_factory(
        agent_id="weather",
        capabilities=[],
        dependencies=[],
    )

    calculator_agent = agent_factory(
        agent_id="calculator",
        capabilities=[],
        dependencies=[],
    )

    container.exists.side_effect = lambda name: True
    container.get.side_effect = lambda name: {
        "weather": weather_agent,
        "calculator": calculator_agent,
    }[name]

    registry = agent_registry_builder(
        container=container,
        agent_names=agent_names,
        agent_selector=mock_agent_selector,
        tool_registry=mock_tool_registry,
    )

    assert isinstance(registry, BusinessAgentRegistry)
    assert registry.get_agent("weather") is weather_agent
    assert registry.get_agent("calculator") is calculator_agent


def test_agent_registry_builder_raises_if_agent_missing(
    container,
    mock_agent_selector,
    mock_tool_registry,
):
    agent_names = ["weather"]

    container.exists.return_value = False

    with pytest.raises(FlotillaConfigurationError):
        agent_registry_builder(
            container=container,
            agent_names=agent_names,
            agent_selector=mock_agent_selector,
            tool_registry=mock_tool_registry,
        )


def test_agent_registry_builder_raises_if_not_business_agent(
    container,
    mock_agent_selector,
    mock_tool_registry,
):
    agent_names = ["weather"]

    container.exists.return_value = True
    container.get.return_value = object()  # not a BaseBusinessAgent

    with pytest.raises(TypeError):
        agent_registry_builder(
            container=container,
            agent_names=agent_names,
            agent_selector=mock_agent_selector,
            tool_registry=mock_tool_registry,
        )

def test_agent_registry_builder_handles_callable_provider(
    container,
    agent_factory,
    mock_agent_selector,
    mock_tool_registry,
):
    agent_names = ["weather"]

    weather_agent = agent_factory(
        agent_id="weather",
        capabilities=[],
        dependencies=[],
    )

    provider = MagicMock(return_value=weather_agent)

    container.exists.return_value = True
    container.get.return_value = provider

    registry = agent_registry_builder(
        container=container,
        agent_names=agent_names,
        agent_selector=mock_agent_selector,
        tool_registry=mock_tool_registry,
    )

    assert registry.get_agent("weather") is weather_agent
    provider.assert_called_once()
