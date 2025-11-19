from langchain.tools import tool
from tools.base_tool import BaseTool
from typing import List
from langchain_core.tools import StructuredTool


class TestTool(BaseTool):
    def __init__(self):
        super().__init__("test_tool", "Test Tool")
        self.configure_count = 0

    @tool
    def my_tool_1(name: str) -> str: 
        """Print the submitted string"""
        print(str)

    @tool
    def my_tool_2() -> str:
        """Second test tool"""
        print(f"Trump sucks")

    
    def _configure_tools(self):
        self.configure_count += 1

    def _register_tools(self) -> List[StructuredTool]:
        return [self.my_tool_1, self.my_tool_2]