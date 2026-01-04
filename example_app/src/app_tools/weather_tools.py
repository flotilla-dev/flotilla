from langchain.tools import tool
from flotilla.tools.decorator_tool_provider import DecoratorToolProvider
import requests
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)


class WeatherTools(DecoratorToolProvider):

    def __init__(self, *, api_key:str, base_url:str, use_api:bool):
        self.api_key = api_key
        self.base_url = base_url
        self.use_api = use_api
        super().__init__(provider_id="weather_tools", provider_name="Weather Tools")

    #define tools
    @tool
    def get_weather_for_location(self, city: str) -> str: 
        """Get weather for a given city"""
        if self.use_api:
            logger.info(f"Lookup the current weather for {city}")
            url = f"{self.base_url}/v1/current.json?key={self.api_key}&q={city}&aqi=no"
            return requests.get(url).text
        else:
            return f"Its always sunny in {city}"
         

    @tool
    def get_user_location(self, name:str) -> str:
        """Retrieve user informatoin based on user id"""
        if self.use_api:
            logger.info(f"Find location for name {name}")
            url = f"{self.base_url}/v1/search.json?key={self.api_key}&q={name}"
            return requests.get(url).text
        else:
            return "Denver" 

    @tool
    def get_forecast_for_location(self, city:str) -> str:
        """Retrieves the 1 day forecast for a location"""
        if self.use_api:
            logger.info(f"Get forecast for city {city}")
            url = f"{self.base_url}/v1/forecast.json?key={self.api_key}&q={city}&days=1&aqi=no&alerts=no"
            return requests.get(url).text
        else:
            return f"Its going to be sunny and warm tomorrow in {city}"
    

