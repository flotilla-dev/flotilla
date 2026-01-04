from langchain_core.tools import StructuredTool
from flotilla.tools.base_tool_provider import BaseToolProvider
from flotilla.utils.logger import get_logger

import asyncio
from typing import List, Dict, Optional
from pydantic import create_model, Field

from mcp import ClientSession
from mcp.client.sse import sse_client
import httpx

logger = get_logger(__name__)


class MCPToolProvider(BaseToolProvider):
    """
    Unified MCP Tool Provider with optional authentication support.
    
    - Supports public and authenticated MCP servers
    - Connects via SSE (Server-Sent Events)
    - Exposes MCP tools as LangChain StructuredTools
    """

    def __init__(
        self,
        provider_id: str,
        provider_name: str,
        server_url: str,
        auth_token: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(provider_id, provider_name)

        self.server_url = server_url
        self.auth_token = auth_token
        self.custom_headers = custom_headers or {}

        self._session = None
        self._sse_url = None

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _configure_tools(self):
        """Initialize connection parameters for remote MCP server."""
        logger.info(f"Configuring connection to remote MCP server: {self.server_url}")

        if not self.server_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid MCP server URL: {self.server_url}")

        self._sse_url = f"{self.server_url}/sse"
        logger.debug(f"MCP SSE endpoint: {self._sse_url}")

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> List[StructuredTool]:
        """
        Connect to MCP server and convert its tools to LangChain StructuredTools.
        (Sync wrapper over async implementation)
        """
        try:
            return asyncio.run(self._async_register_tools())
        except Exception as e:
            logger.error(f"Failed to register MCP tools: {e}")
            return []

    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers including optional authentication."""
        headers = dict(self.custom_headers)

        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        return headers

    async def _async_register_tools(self) -> List[StructuredTool]:
        """Connect to remote MCP server via SSE and fetch tools."""

        tool_list: List[StructuredTool] = []
        headers = self._build_headers()

        try:
            async with httpx.AsyncClient(headers=headers) as http_client:
                async with sse_client(self._sse_url, http_client) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        self._session = session

                        tools_result = await session.list_tools()
                        logger.info(
                            f"Found {len(tools_result.tools)} tools from MCP server"
                        )

                        for mcp_tool in tools_result.tools:
                            langchain_tool = self._create_langchain_tool(mcp_tool, session)
                            tool_list.append(langchain_tool)
                            logger.debug(
                                f"Converted MCP tool '{mcp_tool.name}' to LangChain tool"
                            )

            return tool_list

        except httpx.HTTPError as e:
            logger.error(f"HTTP / Auth error connecting to MCP server: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to remote MCP server: {e}")
            raise

    # ------------------------------------------------------------------
    # Tool Conversion
    # ------------------------------------------------------------------

    def _create_langchain_tool(self, mcp_tool, session: "ClientSession") -> StructuredTool:
        """Convert an MCP tool to a LangChain StructuredTool."""

        field_definitions = {}

        if mcp_tool.inputSchema and "properties" in mcp_tool.inputSchema:
            for param_name, param_info in mcp_tool.inputSchema["properties"].items():
                param_type = self._json_schema_type_to_python(
                    param_info.get("type", "string")
                )
                param_description = param_info.get("description", "")
                is_required = param_name in mcp_tool.inputSchema.get("required", [])

                if is_required:
                    field_definitions[param_name] = (
                        param_type,
                        Field(..., description=param_description),
                    )
                else:
                    field_definitions[param_name] = (
                        Optional[param_type],
                        Field(None, description=param_description),
                    )

        ArgsModel = (
            create_model(f"{mcp_tool.name}Args", **field_definitions)
            if field_definitions
            else None
        )

        async def mcp_tool_function(**kwargs) -> str:
            result = await session.call_tool(mcp_tool.name, arguments=kwargs)

            if result.content:
                return "\n".join(
                    [
                        item.text if hasattr(item, "text") else str(item)
                        for item in result.content
                    ]
                )

            return "No response from tool"

        def sync_wrapper(**kwargs) -> str:
            return asyncio.run(mcp_tool_function(**kwargs))

        if ArgsModel:
            return StructuredTool.from_function(
                func=sync_wrapper,
                name=mcp_tool.name,
                description=mcp_tool.description or f"MCP tool: {mcp_tool.name}",
                args_schema=ArgsModel,
            )
        else:
            return StructuredTool.from_function(
                func=sync_wrapper,
                name=mcp_tool.name,
                description=mcp_tool.description or f"MCP tool: {mcp_tool.name}",
            )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _json_schema_type_to_python(self, json_type: str) -> type:
        """Convert JSON schema type to Python type."""
        type_mapping = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        return type_mapping.get(json_type, str)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self):
        """Clean up remote MCP server connection."""
        logger.info(f"Shutting down MCP provider '{self.provider_name}'")

        if self._session:
            try:
                asyncio.run(self._async_shutdown())
            except Exception as e:
                logger.error(f"Error during MCP shutdown: {e}")

        super().shutdown()

    async def _async_shutdown(self):
        """Async cleanup of MCP resources."""
        if self._session:
            self._session = None
