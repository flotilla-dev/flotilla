from langchain.tools import tool
from tools.tool_factory import ToolFactory
from typing import List
from langchain_core.tools import StructuredTool


class TestTool(ToolFactory):
    def __init__(self):
        super().__init__("test_tool", "Test Tool")
        self.configure_count = 0
        self.tool_1_count = 0
        self.tool_2_count = 9

    @tool
    def my_tool_1(self, name: str) -> str: 
        """Print the submitted string"""
        print(str)
        self.tool_1_count += 1

    @tool
    def my_tool_2(self) -> str:
        """Second test tool"""
        print(f"Trump sucks")
        self.tool_2_count += 1

    
    def _configure_tools(self):
        self.configure_count += 1

    def _register_tools(self) -> List[StructuredTool]:
        return [self.my_tool_1, self.my_tool_2]