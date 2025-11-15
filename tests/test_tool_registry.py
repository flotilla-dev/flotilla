"""
Tests for tool registry
"""
import types
import pytest
from unittest.mock import patch, MagicMock
import pkgutil

from tools.tool_registry import ToolRegistry
from config.settings import Settings


@pytest.fixture
def mock_settings():
    """Create a fake Settings object for testing."""
    mock = MagicMock()
    mock.tool_packages = ["fake_package"]
    mock.tool_recursive = False
    return mock


def test_discover_tools_finds_valid_tools(mock_tool_registry_config):
    """Ensure _discover_tools() finds valid callable tool objects."""    
    registry = ToolRegistry(mock_tool_registry_config)

    tools = registry._discover_tools()

    # Assertions
    assert len(tools) >= 1, "Expected at least one tool to be discovered"
    tool_names = [t.name for t in tools]
    assert "my_tool_1" in tool_names, f"Discovered tools: {tool_names}"
    


def test_loadTools_sets_loaded_flag(mock_tool_registry_config):
    """Ensure loadTools loads tools only once unless forced."""
    # disable automatic discovery to test properly
    mock_tool_registry_config.tool_discovery = False
    registry = ToolRegistry(mock_tool_registry_config)

    with patch.object(registry, "_discover_tools", return_value=["tool1", "tool2"]) as mock_discover:
        assert registry._loaded is False
        assert len(registry._tools) == 0
        # First load
        registry.load_tools(force_reload=True)
        assert registry._loaded is True
        assert registry._tools == ["tool1", "tool2"]
        mock_discover.assert_called_once()

        # With force_reload=True, it should call again
        registry.load_tools(force_reload=True)
        assert mock_discover.call_count == 2



def test_getToolNames_returns_tool_names(mock_tool_registry_config):
    """Ensure getToolNames() extracts the 'name' property correctly."""
    fake_tool_1 = MagicMock(name="tool1")
    fake_tool_1.name = "tool1"
    fake_tool_2 = MagicMock(name="tool2")
    fake_tool_2.name = "tool2"

    registry = ToolRegistry(mock_tool_registry_config)
    registry._loaded = True
    registry._tools = [fake_tool_1, fake_tool_2]

    names = registry.get_tool_names()
    assert names == ["tool1", "tool2"]

def test_tool_registration(mock_tool_registry_config):
    mock_tool = MagicMock(name="tool_1")
    mock_tool.name = "tool_1"
    registry = ToolRegistry(mock_tool_registry_config)
    registry._loaded = True
    # start with empty tool list
    registry._tools = []
    assert len(registry.get_all_tools()) == 0
    
    registry.register_tool(mock_tool)
    assert len(registry.get_all_tools()) == 1

    registry.unregister_tool(mock_tool.name)
    assert len(registry.get_all_tools()) == 0


def test_get_tools_by_filter(mock_tool_registry_config):
    # add mock tools
    fake_tool_1 = MagicMock(name="tool1")
    fake_tool_1.name = "tool1"
    fake_tool_2 = MagicMock(name="tool2")
    fake_tool_2.name = "tool2"
    fake_tool_3 = MagicMock(name="tool3")
    fake_tool_3.name = "tool3"
    fake_tool_4 = MagicMock(name="tool4")
    fake_tool_4.name = "tool4"

    registry = ToolRegistry(mock_tool_registry_config)
    registry._loaded = True
    registry._tools = [fake_tool_1, fake_tool_2, fake_tool_3, fake_tool_4]

    filtered_tools = registry.get_tools(filter_tools)
    assert filtered_tools is not None
    assert len(filtered_tools) == 1
    assert filtered_tools[0] == fake_tool_3


def filter_tools(tool:object):
    if (tool.name == "tool3"):
        return True
    else:
        return False