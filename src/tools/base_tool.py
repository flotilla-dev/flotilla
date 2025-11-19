
from config.config_models import ToolConfig
from abc import ABC, abstractmethod
from typing import List
from langchain_core.tools import StructuredTool
from utils.logger import get_logger

logger = get_logger(__name__)

class BaseTool(ABC):
    def __init__(self, id:str, name:str):
        self.tool_id = id
        self.tool_name = name
        self.config = None
        self.tools = None

    def configure(self, config:ToolConfig):
        """
        Lifecycle method that is called when the BaseTool instance is registered with the ToolRegistry.  This class will save the ToolConfig to self.config and
        then call in order _configure_tools() and _register_tools().  Subclasses should implement these methods in order property configure and register tool(s) for 
        use with Agents.

        Args:
            config: The ToolConfig for this specific Tool that is keyed off the tool_id of the Tool

        """
        self.config = config
        self._configure_tools()
        self.tools = self._register_tools()
    

    def _configure_tools(self):
        """
        Method that should be overridden by subclasses in order to configure all tools attached to this Tool class
        k"""
        logger.debug(f"Empty _configure_tools called for Tool {self.tool_name}")
        
    def shutdown(self):
        """Lifecycle method that allows the Tool class to perform any necessary cleanup during system shutdown"""
        logger.debug(f"Perform empty shutdown on Tool {self.tool_name}")


    # --------------------------
    # Astract methods to be implemented by subclasses
    # --------------------------

    @abstractmethod
    def _register_tools(self) -> List[StructuredTool]:
        """
        Returns a List of all Tool functions that are defined on the subclass
        """
        pass