from langchain.tools import tool, ToolRuntime
from my_context import Context
from tools.base_tool import BaseTool

class WeatherTool(BaseTool):
    def __init__(self):
        super().__init__("weather_tools", "Weather Tools")

    def _register_tools(self):
        return [self.get_user_location, self.get_weather_for_location]

    #define tools
    @tool
    def get_weather_for_location(city: str) -> str: 
        """Get weather for a given city"""
        return f"It's always sunny in {city}"

    @tool
    def get_user_location() -> str:
        """Retrieve user informatoin based on user id"""
        return "Chicago" 
