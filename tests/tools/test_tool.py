from langchain.tools import tool

@tool
def my_tool_1(name: str) -> str: 
    """Print the submitted string"""
    print(str)

@tool
def my_tool_2() -> str:
    """Second test tool"""
    print(f"Trump sucks")