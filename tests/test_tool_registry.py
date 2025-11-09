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


def test_discover_tools_finds_valid_tools():
    """Ensure _discover_tools() finds valid callable tool objects."""
    test_settings = Settings()
    test_settings.tool_packages = ["tests.tools"]

    registry = ToolRegistry(test_settings)

    tools = registry._discover_tools()

    # Assertions
    assert len(tools) >= 1, "Expected at least one tool to be discovered"
    tool_names = [t.name for t in tools]
    assert "my_tool_1" in tool_names, f"Discovered tools: {tool_names}"
    


def test_loadTools_sets_loaded_flag(mock_settings):
    """Ensure loadTools loads tools only once unless forced."""
    registry = ToolRegistry(mock_settings)

    with patch.object(registry, "_discover_tools", return_value=["tool1", "tool2"]) as mock_discover:
        # First load
        registry.loadTools()
        assert registry._loaded is True
        assert registry._tools == ["tool1", "tool2"]
        mock_discover.assert_called_once()

        # Second load without force_reload should not re-call _discover_tools
        registry.loadTools()
        mock_discover.assert_called_once()

        # With force_reload=True, it should call again
        registry.loadTools(force_reload=True)
        assert mock_discover.call_count == 2


def test_getAllTools_triggers_lazy_load(mock_settings):
    """Ensure getAllTools() triggers a load if not already loaded."""
    registry = ToolRegistry(mock_settings)

    with patch.object(registry, "loadTools") as mock_load:
        registry._loaded = False
        registry.getAllTools()
        mock_load.assert_called_once()


def test_getToolNames_returns_tool_names(mock_settings):
    """Ensure getToolNames() extracts the 'name' property correctly."""
    fake_tool_1 = MagicMock(name="tool1")
    fake_tool_1.name = "tool1"
    fake_tool_2 = MagicMock(name="tool2")
    fake_tool_2.name = "tool2"

    registry = ToolRegistry(mock_settings)
    registry._loaded = True
    registry._tools = [fake_tool_1, fake_tool_2]

    names = registry.getToolNames()
    assert names == ["tool1", "tool2"]