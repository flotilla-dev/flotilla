from config.config_models import ToolConfig
from abc import ABC, abstractmethod
from typing import List
from langchain_core.tools import StructuredTool
from utils.logger import get_logger
import inspect

logger = get_logger(__name__)

class ToolFactory(ABC):
    def __init__(self, id: str, name: str):
        self.tool_id = id
        self.tool_name = name
        self.config: ToolConfig = None
        self.tools: List[StructuredTool] = None

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------

    def configure(self, config: ToolConfig):
        """
        Called when the tool is registered.
        Saves config, runs subclass configuration, and then registers
        all @tool methods.
        """
        self.config = config
        self._configure_tools()
        if self.config.tool_discovery:
            self.tools = self._register_tools()

    def _configure_tools(self):
        """Subclass override to configure tool (load API keys, URLs, etc.)."""
        logger.debug(f"Empty _configure_tools called for Tool {self.tool_name}")

    def shutdown(self):
        """Optional hook for cleanup."""
        logger.debug(f"Perform empty shutdown on Tool {self.tool_name}")

    # ------------------------------------------------------------
    # Automatic registration of @tool instance methods
    # ------------------------------------------------------------

    def _register_tools(self) -> List[StructuredTool]:
        """
        Automatically detects instance methods decorated with LangChain's @tool 
        and wraps them into StructuredTool objects with `self` correctly bound.
        
        This ensures:
        - `self` is NOT part of the tool schema
        - Tools can access instance state (API keys, config, etc.)
        - Developers can simply write @tool methods normally
        """
        tool_list = []

        for attr_name, member in inspect.getmembers(self):
            # LangChain tools are StructuredTool instances
            if isinstance(member, StructuredTool):
                # get the raw function
                original_fn = member.func
                # Bind `self` to the function so it becomes a proper method
                bound_fn = original_fn.__get__(self, self.__class__)

                tool = StructuredTool.from_function(
                    func=bound_fn,
                    name=member.name,
                    description=member.description
                )

                tool_list.append(tool)
        return tool_list
    
    def get_tool(self, name: str) -> StructuredTool:
        """
        Retrieves a tool from the internal collection of tools after registration is complete
        """
        return next(t for t in self.tools if t.name == name)
    
    def get_tool_names(self) -> List[str]:
        """
        Returns a list of the tools that have been registered 
        """
        names = []
        for t in self.tools:
            names.append(t.name)

        return names
