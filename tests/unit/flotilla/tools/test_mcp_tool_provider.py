"""
Updated PyTest suite for unified MCPToolProvider
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import List
from langchain_core.tools import StructuredTool

from flotilla.tools.mcp_tool_provider import MCPToolProvider   # unified version
from flotilla.tools.tool_config import ToolConfig


# ================================================================
# Mock MCP Objects
# ================================================================
'''
class MockMCPTool:
    """Mock MCP tool definition used for all tests."""
    def __init__(self, name: str, description: str, input_schema: dict = None):
        self.name = name
        self.description = description
        self.inputSchema = input_schema or {
            "type": "object",
            "properties": {},
            "required": []
        }


class MockListToolsResult:
    def __init__(self, tools: List[MockMCPTool]):
        self.tools = tools


class MockCallToolResult:
    def __init__(self, text_content: str):
        self.content = [MockContent(text_content)]


class MockContent:
    def __init__(self, text: str):
        self.text = text


class MockClientSession:
    """Mock MCP ClientSession."""
    def __init__(self, tools: List[MockMCPTool]):
        self._tools = tools
        self.initialized = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def initialize(self):
        self.initialized = True

    async def list_tools(self):
        return MockListToolsResult(self._tools)

    async def call_tool(self, name: str, arguments: dict):
        return MockCallToolResult(f"Result from {name} with {arguments}")


# ================================================================
# Fixtures
# ================================================================

@pytest.fixture
def mock_config():
    config = Mock(spec=ToolConfig)
    config.tool_discovery = True
    return config


@pytest.fixture
def mock_mcp_tools():
    return [
        MockMCPTool(
            name="read_file",
            description="Read contents of a file",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path"}},
                "required": ["path"]
            }
        ),
        MockMCPTool(
            name="list_directory",
            description="List files in a directory",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path"},
                    "recursive": {"type": "boolean", "description": "Recursive listing"}
                },
                "required": ["path"]
            }
        ),
        MockMCPTool(
            name="simple_tool",
            description="A simple tool",
            input_schema={"type": "object", "properties": {}}
        ),
    ]


@pytest.fixture
def mock_sse_context():
    """Unified SSE context manager mock (NO async wrapper!)."""
    mock_read = AsyncMock()
    mock_write = AsyncMock()

    class SSEContext:
        async def __aenter__(self):
            return (mock_read, mock_write)

        async def __aexit__(self, exc_type, exc, tb):
            pass

    return SSEContext()


# ================================================================
# Constructor Tests
# ================================================================

def test_constructor_basic():
    provider = MCPToolProvider(
        provider_id="test",
        provider_name="Test Provider",
        server_url="https://server.example.com"
    )

    assert provider.provider_id == "test"
    assert provider.provider_name == "Test Provider"
    assert provider.server_url == "https://server.example.com"
    assert provider._session is None


def test_constructor_with_auth():
    provider = MCPToolProvider(
        provider_id="secure",
        provider_name="Secure Provider",
        server_url="https://secure.example.com",
        auth_token="ABC123",
        custom_headers={"X-API-Version": "v1"}
    )

    assert provider.auth_token == "ABC123"
    assert provider.custom_headers["X-API-Version"] == "v1"


# ================================================================
# _configure_tools Tests
# ================================================================

def test_configure_tools_creates_sse_url():
    provider = MCPToolProvider("test", "Test", "https://server.com")
    provider._configure_tools()
    assert provider._sse_url == "https://server.com/sse"


def test_configure_tools_rejects_invalid_url():
    provider = MCPToolProvider("test", "Test", "invalid")
    with pytest.raises(ValueError):
        provider._configure_tools()


# ================================================================
# _async_register_tools Tests
# ================================================================

@pytest.mark.asyncio
async def test_async_register_tools_basic(mock_mcp_tools, mock_sse_context):
    provider = MCPToolProvider(
        provider_id="test",
        provider_name="Test Provider",
        server_url="https://server.com",
    )
    provider._sse_url = "https://server.com/sse"

    with patch("tools.mcp_tool_provider.httpx.AsyncClient") as mock_http, \
         patch("tools.mcp_tool_provider.sse_client") as mock_sse, \
         patch("tools.mcp_tool_provider.ClientSession") as mock_session_class:

        mock_http.return_value.__aenter__.return_value = AsyncMock()
        mock_sse.return_value = mock_sse_context
        mock_session_class.return_value.__aenter__.return_value = MockClientSession(mock_mcp_tools)

        tools = await provider._async_register_tools()

        assert len(tools) == 3
        assert all(isinstance(t, StructuredTool) for t in tools)


@pytest.mark.asyncio
async def test_async_register_tools_with_auth_headers(mock_mcp_tools, mock_sse_context):
    provider = MCPToolProvider(
        provider_id="secure",
        provider_name="Secure Provider",
        server_url="https://secure.com",
        auth_token="TOKEN123",
        custom_headers={"X-Test": "1"}
    )
    provider._sse_url = "https://secure.com/sse"

    with patch("tools.mcp_tool_provider.httpx.AsyncClient") as mock_http, \
         patch("tools.mcp_tool_provider.sse_client") as mock_sse, \
         patch("tools.mcp_tool_provider.ClientSession") as mock_session_class:

        mock_http.return_value.__aenter__.return_value = AsyncMock()
        mock_sse.return_value = mock_sse_context
        mock_session_class.return_value.__aenter__.return_value = MockClientSession(mock_mcp_tools)

        await provider._async_register_tools()

        # Confirm headers were applied
        args, kwargs = mock_http.call_args
        headers = kwargs["headers"]

        assert headers["Authorization"] == "Bearer TOKEN123"
        assert headers["X-Test"] == "1"


@pytest.mark.asyncio
async def test_async_register_tools_raises_http_failure():
    provider = MCPToolProvider("t", "Test", "https://server.com")
    provider._sse_url = "https://server.com/sse"

    with patch("tools.mcp_tool_provider.httpx.AsyncClient") as mock_http:
        mock_http.return_value.__aenter__.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            await provider._async_register_tools()


# ================================================================
# create_langchain_tool Tests
# ================================================================

def test_create_langchain_tool_with_schema(mock_mcp_tools):
    provider = MCPToolProvider("t", "Test", "https://server.com")
    session = Mock()

    lc_tool = provider._create_langchain_tool(mock_mcp_tools[0], session)
    assert isinstance(lc_tool, StructuredTool)
    assert lc_tool.name == "read_file"


def test_create_langchain_tool_no_parameters(mock_mcp_tools):
    provider = MCPToolProvider("t", "Test", "https://server.com")
    session = Mock()

    lc_tool = provider._create_langchain_tool(mock_mcp_tools[2], session)
    assert isinstance(lc_tool, StructuredTool)
    assert lc_tool.name == "simple_tool"


# ================================================================
# Edge Cases
# ================================================================

def test_get_tools_before_config():
    provider = MCPToolProvider("t", "Test", "https://server.com")
    assert provider.get_tools() == []


def test_shutdown_without_session():
    provider = MCPToolProvider("t", "Test", "https://server.com")
    provider.shutdown()  # should not throw
'''