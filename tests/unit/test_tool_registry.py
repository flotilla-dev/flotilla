"""
Tests for tool registry
"""
import types
import pytest
from unittest.mock import patch, MagicMock
import pkgutil

from tools.tool_registry import ToolRegistry
from config.settings import Settings
from tools.base_tool import BaseTool
from langchain_core.tools import tool


class MockTool(BaseTool):
    def __init__(self, id:str | None = "mock_1", name:str | None = "Mock Tool"):
        """COnstructor"""
        super().__init__(id, name)
    
    def _register_tools(self):
        """Returns the list of tools"""
        return [self.mock_tool]
    
    @tool
    def mock_tool(self):
        """Fake tool logic"""
        pass


@pytest.mark.unit
@pytest.mark.registry
class TestToolRegistry:
    def test_discover_tools_finds_valid_tools(self, mock_tool_registry_config):
        """Ensure _discover_tools() finds valid callable tool objects."""    
        registry = ToolRegistry(mock_tool_registry_config)

        tools = registry._tools
        # Assertions
        assert len(tools) >= 1, "Expected at least one tool to be discovered"
        tool_names = [t.tool_name for t in tools]
        assert "Test Tool" in tool_names, f"Discovered tools: {tool_names}"
        


    def test_loadTools_sets_loaded_flag(self, mocker, mock_tool_registry_config):
        """Ensure loadTools loads tools only once unless forced."""
        # disable automatic discovery to test properly
        mock_tool_registry_config.tool_discovery = False
        registry = ToolRegistry(mock_tool_registry_config)
        spy = mocker.spy(registry, "_discover_tools")

        assert registry._loaded is False
        assert len(registry._tools) == 0
        # First load
        registry.load_tools(force_reload=True)
        assert registry._loaded is True
        assert spy.call_count == 1

            # With force_reload=True, it should call again
        registry.load_tools(force_reload=True)
        assert spy.call_count == 2


    def test_get_all_tools_returns_tools(self, mock_tool_registry_config):
        registry = ToolRegistry(mock_tool_registry_config)

        tools = registry.get_all_tools()
        assert tools
        assert len(tools) == 2

    def test_tool_names_returns_tool_names(self, mock_tool_registry_config):
        registry = ToolRegistry(mock_tool_registry_config)

        tool_names = registry.get_tool_names()

        assert tool_names
        assert len(tool_names) == 2
        assert tool_names == ["my_tool_1", "my_tool_2"]


    def test_tool_registration(self, mock_tool_registry_config):
        mock_tool_registry_config.tool_discovery = False
        registry = ToolRegistry(mock_tool_registry_config)
        tool = MockTool()

        assert registry
        assert not registry._loaded
        assert registry._tools is not None
        assert len(registry._tools) == 0

        registry.register_tool(tool)

        assert registry._loaded
        assert len(registry._tools) == 1
        

    def test_get_tools_by_filter(self, mock_tool_registry_config):
        # load standard test tools
        registry = ToolRegistry(mock_tool_registry_config)
        # add mock tools
        mock_tool = MockTool("tool_1", "Tool1")
        registry.register_tool(mock_tool)


        filtered_tools = registry.get_tools(self.filter_tools)
        assert filtered_tools is not None
        assert len(filtered_tools) == 1
        assert filtered_tools[0] == mock_tool.mock_tool


    @staticmethod
    def filter_tools(tool) -> bool:
        return tool.name == "mock_tool"
    

    def test_shutdown_calls_shutdown_on_base_tools(self, caplog):
        # --- Setup registry ---
        registry = ToolRegistry(config=MagicMock())

        # Create mock BaseTool instance
        mock_tool = MagicMock(spec=BaseTool)
        mock_tool.tool_name = "MockTool"

        # Fake non-tool object
        non_tool = "not-a-tool"

        # Inject both into registry
        registry._tools = [mock_tool, non_tool]

        # --- Run shutdown ---
        with caplog.at_level("DEBUG"):
            registry.shutdown()

        # --- Assertions ---
        # BaseTool.shutdown() should be called
        mock_tool.shutdown.assert_called_once()

        # Non-tools should not cause errors (no shutdown call)
        # And log a warning
        assert any(
            "Non BaseTool in tools" in record.message
            for record in caplog.records
        )
