from flotilla.config_models import ToolConfig
from abc import ABC, abstractmethod
from typing import List, Optional
from langchain_core.tools import StructuredTool
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)

class BaseToolProvider(ABC):
    """
    Abstract base class for tool providers.
    
    Tool providers encapsulate one or more LangChain tools and handle their
    configuration, lifecycle, and registration.
    """

    def __init__(self, *,provider_id: str, provider_name: str, config:ToolConfig):
        self.provider_id = provider_id
        self.provider_name = provider_name
        self.config = config
        self._configure_tools()
        self.tools = self._register_tools()
        logger.info(f"Provider '{self.provider_name}' registered {len(self.tools)} tools")

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    
    @abstractmethod
    def _configure_tools(self):
        """Subclass override to configure tools (load API keys, URLs, etc.)."""
        pass

    @abstractmethod
    def _register_tools(self) -> List[StructuredTool]:
        """Subclass override to register and return tools."""
        pass

    def shutdown(self):
        """Optional hook for cleanup when provider is unregistered."""
        logger.debug(f"Shutting down tool provider '{self.provider_name}'")

    # ------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------
    
    def get_tools(self) -> List[StructuredTool]:
        """Returns all registered tools from this provider."""
        return self.tools if self.tools else []
    
    def get_tool(self, name: str) -> Optional[StructuredTool]:
        """Retrieves a specific tool by name."""
        if not self.tools:
            return None
        return next((t for t in self.tools if t.name == name), None)
    
    def get_tool_names(self) -> List[str]:
        """Returns list of tool names."""
        return [t.name for t in self.tools] if self.tools else []
    




