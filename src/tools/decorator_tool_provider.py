
from typing import List
from tools.base_tool_provider import BaseToolProvider
from langchain_core.tools import StructuredTool
from utils.logger import get_logger
import inspect


logger = get_logger(__name__)

class DecoratorToolProvider(BaseToolProvider):
    """
    Tool provider that discovers tools using @tool decorators on instance methods.
    This is your original implementation pattern.
    """
    
    def _configure_tools(self):
        """Default implementation - subclasses can override."""
        logger.debug(f"Default _configure_tools for '{self.provider_name}'")

    

    def _register_tools(self) -> List[StructuredTool]:
        """
        Automatically detects instance methods decorated with @tool
        and wraps them into StructuredTool objects.
        """
        tool_list = []

        for attr_name, member in inspect.getmembers(self):
            if isinstance(member, StructuredTool):
                original_fn = member.func
                bound_fn = original_fn.__get__(self, self.__class__)

                tool = StructuredTool.from_function(
                    func=bound_fn,
                    name=member.name,
                    description=member.description
                )

                tool_list.append(tool)
                logger.debug(f"Registered tool '{member.name}' from '{self.provider_name}'")
        
        return tool_list