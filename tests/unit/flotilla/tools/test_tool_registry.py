"""
Tests for tool registry
"""
import pytest
from flotilla.tools.tool_registry import ToolRegistry
from flotilla.tools.base_tool_provider import BaseToolProvider

from langchain_core.tools import tool

pytestmark = pytest.mark.unit


class MockTool(BaseToolProvider):
    def __init__(self, id:str | None = "mock_1", name:str | None = "Mock Tool"):
        """COnstructor"""
        super().__init__(provider_id=id, provider_name=name,config= None)
        self.shutdown_call = False
    
    def _register_tools(self):
        """Returns the list of tools"""
        return [self.mock_tool]
    
    def _configure_tools(self):
        return super()._configure_tools()
    
    def shutdown(self):
        self.shutdown_call = True
    
    @tool
    def mock_tool(self):
        """Fake tool logic"""
        pass



def test_empty_provider_list():
    registry = ToolRegistry(tool_providers=[])

    providers = registry._providers
    # Assertions
    assert len(providers) == 0, "Expected zero providers in ToolRegistry"
    

def test_non_null_provider_list():
    providers = [MockTool]
    registry = ToolRegistry(tool_providers=providers)

    assert len(registry._providers) == 1, "ToolRegistry expected to have 1 provider"



def test_get_all_tools_returns_tools():
    mock_provider = MockTool()
    providers = [mock_provider]
    registry = ToolRegistry(tool_providers=providers)

    tools = registry.get_all_tools()
    assert tools
    assert len(tools) == 1

def test_tool_names_returns_tool_names():
    mock_provider = MockTool()
    providers = [mock_provider]
    registry = ToolRegistry(tool_providers=providers)

    tool_names = registry.get_tool_names()

    assert tool_names
    assert len(tool_names) == 1
    assert tool_names == ["mock_tool"]

    

def test_get_tools_by_filter():
    mock_provider = MockTool()
    providers = [mock_provider]
    # load standard test tools
    registry = ToolRegistry(tool_providers=providers)

    filtered_tools = registry.get_tools(filter_tools)
    assert filtered_tools is not None
    assert len(filtered_tools) == 1
    assert filtered_tools[0] == mock_provider.mock_tool


@staticmethod
def filter_tools(tool) -> bool:
    return tool.name == "mock_tool"


def test_shutdown_calls_shutdown_on_base_tools(caplog):
    # --- Setup registry ---

    mock_provider1 = MockTool()
    mock_provider2 = MockTool()
    providers = [mock_provider1, mock_provider2]
    registry = ToolRegistry(tool_providers=providers)

    assert not mock_provider1.shutdown_call
    assert not mock_provider2.shutdown_call

    registry.shutdown()

    assert mock_provider1.shutdown_call
    assert mock_provider2.shutdown_call 


def test_get_tool_by_name_returns_tool():
    mock_provider = MockTool()
    registry = ToolRegistry(tool_providers=[mock_provider])

    tool = registry.get_tool_by_name("mock_tool")

    assert tool is mock_provider.mock_tool


def test_get_tool_by_name_returns_none_if_missing():
    mock_provider = MockTool()
    registry = ToolRegistry(tool_providers=[mock_provider])

    tool = registry.get_tool_by_name("does_not_exist")

    assert tool is None


def test_non_base_tool_provider_is_ignored():
    class NotAProvider:
        pass

    registry = ToolRegistry(tool_providers=[NotAProvider()])

    tools = registry.get_all_tools()

    assert tools == []


def test_shutdown_skips_non_base_tool_provider(caplog):
    class NotAProvider:
        pass

    registry = ToolRegistry(tool_providers=[NotAProvider()])

    registry.shutdown()

    assert "skipping shutdown call" in caplog.text.lower()
