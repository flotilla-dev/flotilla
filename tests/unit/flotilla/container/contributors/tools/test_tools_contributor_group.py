import pytest

from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.container.contributors.tools.group import ToolsContributorGroup
from flotilla.builders.default_builders import default_tool_registry_builder


pytestmark = pytest.mark.unit

def test_tools_contributor_group_registers_tools(tool_provider_factory, tool_factory):
    settings = FlotillaSettings({
        "tools": {
            "mock_tool": {
                "builder": "mock"
            }
        }
    })

    container = FlotillaContainer(settings)
    container.register_builder("tool_registry", default_tool_registry_builder)
    # register mock builder
    mock_tool = tool_factory(name="mock_tool")
    def mock_tool_builder(config, container):
        return tool_provider_factory(provider_id="mock_provider", config= None, tools= [mock_tool])

    container.register_builder("mock", mock_tool_builder)

    group = ToolsContributorGroup()
    group.contribute(container)
    group.validate(container)

    registry = container.di.tool_registry()

    assert registry.get_tool_by_name("mock_tool") == mock_tool

def test_tools_contributor_group_missing_builder_raises():
    settings = FlotillaSettings({
        "tools": {
            "bad_tool": {
                "builder": "missing"
            }
        }
    })

    container = FlotillaContainer(settings)
    group = ToolsContributorGroup()

    with pytest.raises(Exception):
        group.contribute(container)


def test_tools_contributor_group_with_no_tools_is_noop():
    settings = FlotillaSettings({})

    container = FlotillaContainer(settings)
    group = ToolsContributorGroup()
    container.register_builder("tool_registry", default_tool_registry_builder)

    group.contribute(container)
    group.validate(container)

    registry = container.di.tool_registry()
    assert registry.get_all_tools() == []


def test_tools_contributor_group_context_is_not_on_container():
    settings = FlotillaSettings({})

    container = FlotillaContainer(settings)
    group = ToolsContributorGroup()
    container.register_builder("tool_registry", default_tool_registry_builder)

    group.contribute(container)

    assert not hasattr(container, "context")
