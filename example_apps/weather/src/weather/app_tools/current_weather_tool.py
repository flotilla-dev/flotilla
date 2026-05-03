import requests
from flotilla.utils.logger import get_logger
from flotilla.tools.decorated_flotilla_tool import DecoratedFlotillaTool
from flotilla.tools.tool_decorators import tool_call

logger = get_logger(__name__)


class CurrentWeatherTool(DecoratedFlotillaTool):

    def __init__(self, *, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        super().__init__()

    @property
    def name(self) -> str:
        return "Current weather tool"

    @property
    def llm_description(self) -> str:
        return """    
Retrieve the current weather conditions for a city.

Use this tool when the user asks about the current weather, temperature,
or conditions in a specific city.

Input:
- city: the name of the city.

Returns:
Current weather information including temperature, conditions,
humidity, and wind.
"""

    # define tools
    @tool_call
    def get_current_weather(self, city: str) -> str:
        """Get weather for a given city"""
        logger.info("Lookup current weather for city '%s'", city)
        url = f"{self.base_url}/v1/current.json?key={self.api_key}&q={city}&aqi=no"
        return requests.get(url).text
