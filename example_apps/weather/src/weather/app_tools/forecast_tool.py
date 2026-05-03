from flotilla.tools.flotilla_tool import FlotillaTool
from flotilla.utils.logger import get_logger
import requests

logger = get_logger(__name__)


class ForecastTool(FlotillaTool):

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        super().__init__()

    @property
    def name(self) -> str:
        return "Forecast Tool"

    @property
    def llm_description(self) -> str:
        return """
Retrieve the weather forecast for a city.

Use this tool when the user asks about future weather conditions
(e.g., tomorrow, later today, or upcoming days). For current
conditions, use the current weather tool instead.

Input:
- city: the name of the city.

Returns:
An XML document containing structured forecast information,
including upcoming temperatures, conditions, and precipitation.
"""

    def execution_callable(self):
        return self.get_forecast

    def get_forecast(self, city: str) -> str:
        """Retrieves the 1 day forecast for a location"""
        logger.info("Get forecast for city '%s'", city)
        url = f"{self.base_url}/v1/forecast.json?key={self.api_key}&q={city}&days=1&aqi=no&alerts=no"
        return requests.get(url).text
