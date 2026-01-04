import pytest
from unittest.mock import MagicMock

from flotilla.agents.wiring.agent_context import AgentContext
from flotilla.agents.wiring.agent_registry_contributor import AgentRegistryContributor
from flotilla.flotilla_configuration_error import FlotillaConfigurationError
from flotilla.container.flotilla_container import FlotillaContainer


@pytest.fixture
def container():
    container = MagicMock(spec=FlotillaContainer)
    container.wire_infrastructure = MagicMock()
    container.get_builder = MagicMock()
    container.get = MagicMock()
    return container


def test_agent_registry_contributor_wires_registry(container):
    contributor = AgentRegistryContributor()
    context = AgentContext(agent_names=["weather", "calculator"])

    mock_builder = MagicMock(name="agent_registry_builder")
    mock_tool_registry = MagicMock(name="tool_registry")
    mock_agent_selector = MagicMock(name="agent_selector")

    container.get_builder.return_value = mock_builder
    container.get.side_effect = [mock_tool_registry, mock_agent_selector]

    contributor.contribute(container, context)

    container.get_builder.assert_called_once_with("agent_registry")

    # get() called twice: tool_registry, agent_selector
    assert container.get.call_count == 2

    container.wire_infrastructure.assert_called_once_with(
        name="agent_registry",
        builder=mock_builder,
        agent_names=["weather", "calculator"],
        tool_registry=mock_tool_registry,
        agent_selector=mock_agent_selector,
    )


def test_agent_registry_contributor_raises_if_builder_missing(container):
    contributor = AgentRegistryContributor()
    context = AgentContext(agent_names=["weather"])

    container.get_builder.return_value = None

    with pytest.raises(FlotillaConfigurationError):
        contributor.contribute(container, context)

    container.wire_infrastructure.assert_not_called()


def test_agent_registry_contributor_validate_raise_error(container):
    contributor = AgentRegistryContributor()
    context = AgentContext()
    container.exists.return_value = False  # ← critical line

    with pytest.raises(FlotillaConfigurationError):
        # should not raise
        contributor.validate(container=container, context=context)
