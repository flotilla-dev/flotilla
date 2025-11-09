from langchain.tools import tool, ToolRuntime
from my_context import Context


#define tools
@tool
def get_weather_for_location(city: str) -> str: 
    """Get weather for a given city"""
    return f"It's always sunny in {city}"

@tool
def get_user_location() -> str:
    """Retrieve user informatoin based on user id"""
    return "Chicago" 
