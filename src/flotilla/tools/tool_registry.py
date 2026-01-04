from typing import List, Callable, Optional

from langchain_core.tools import StructuredTool

from flotilla.tools.base_tool_provider import BaseToolProvider
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)

class ToolRegistry:
    """
    Registry object for all Tools that can be used by an Agent within the Flotilla framework.  
    """
    def __init__(self, *, tool_providers: List[BaseToolProvider]):
        self._providers = tool_providers
    

    def get_all_tools(self) -> List[StructuredTool]:
        """
        Returns a flattened list of all StructuredTool objects provided
        by every registered ToolProvider instance.
        """
        all_structured_tools: List[StructuredTool] = []

        for provider in self._providers:  # each is a BaseTool
            if isinstance(provider, BaseToolProvider):
                all_structured_tools.extend(provider.tools)

        return all_structured_tools


    def get_tools(self, filter_function: Callable[[StructuredTool], bool]) -> List[StructuredTool]:
        """Returns a list of Tools based on the filter function that was provided"""
        return list(filter(filter_function, self.get_all_tools()))


    def get_tool_by_name(self, name: str) -> Optional[StructuredTool]:
        """
        Returns a single StructuredTool matching the given name, or None if not found.
        """
        tools = self.get_tools(lambda tool: tool.name == name)
        return tools[0] if tools else None        


    def get_tool_names(self) -> List[str]:
        """Return just the names of all tools."""
        return [t.name for t in self.get_all_tools()]
    

    def shutdown(self):
        """Lifecycle method to cleanup resources when the application is finished"""
        logger.info("Shutdown the ToolRegistry")
        for provider in self._providers:
            if provider and isinstance(provider, BaseToolProvider):
                logger.debug(f"Calling shutdown on Tool {provider.provider_name}")
                provider.shutdown()
            else:
                logger.warning(f"Non BaseTool in tools {provider}, skipping shutdown call")
 