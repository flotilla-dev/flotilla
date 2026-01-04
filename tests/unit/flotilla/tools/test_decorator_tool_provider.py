import pytest
from langchain_core.tools import tool, StructuredTool

from flotilla.tools.decorator_tool_provider import DecoratorToolProvider
from flotilla.tools.tool_config import ToolConfig


class SampleDecoratorProvider(DecoratorToolProvider):
    @tool
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @tool
    def echo(self, value: str) -> str:
        """Echo value."""
        return value

    def helper(self):
        return "not a tool"

def create_provider():
    return SampleDecoratorProvider(
        provider_id="sample",
        provider_name="SampleProvider",
        config=ToolConfig(),
    )

def test_discovers_decorated_tools():
    provider = create_provider()

    tools = provider.get_tools()

    assert len(tools) == 2
    assert all(isinstance(t, StructuredTool) for t in tools)
    assert set(provider.get_tool_names()) == {"add", "echo"}

def test_tools_are_bound_to_instance():
    provider = create_provider()

    add_tool = provider.get_tool("add")
    assert add_tool is not None

    result = add_tool.invoke({"a": 2, "b": 3})

    assert result == 5

def test_tool_metadata_preserved():
    provider = create_provider()

    add_tool = provider.get_tool("add")

    assert add_tool.name == "add"
    assert add_tool.description == "Add two numbers."

class EmptyDecoratorProvider(DecoratorToolProvider):
    def helper(self):
        return "no tools"

def test_provider_with_no_tools():
    provider = EmptyDecoratorProvider(
        provider_id="empty",
        provider_name="EmptyProvider",
        config=ToolConfig(),
    )

    assert provider.get_tools() == []
    assert provider.get_tool("anything") is None
    assert provider.get_tool_names() == []

def test_tools_are_not_shared_between_instances():
    provider1 = create_provider()
    provider2 = create_provider()

    assert provider1.get_tools() is not provider2.get_tools()

