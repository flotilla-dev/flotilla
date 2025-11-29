from langchain.tools import tool, ToolRuntime
from my_context import Context
from tools.base_tool import BaseTool
import requests


class WeatherTools(BaseTool):

    def __init__(self):
        super().__init__("weather_tools", "Weather Tools")

    def _configure_tools(self):
        # get data from the tool config to build the URLs
        self.api_key = self.config.tool_configuration.get("WEATHER_API", {}).get("KEY", None)
        if self.api_key is None:
            raise KeyError("WeatherTools: API Key: WEATHER_API.KEY was not found in configuration")
        self.base_url = self.config.tool_configuration.get("WEATHER_API", {}).get("BASE_URL", None)
        if self.base_url is None:
            raise KeyError("WeatherTools: Base URL: WEATHER_API.BASE_URL was not found in configuration")


    #define tools
    @tool
    def get_weather_for_location(self, city: str) -> str: 
        """Get weather for a given city"""
        # https://api.weatherapi.com/v1/current.json?key=6156d81302004b8e9ae223109252611&q=Chicago&aqi=no
        url = f"{self.base_url}/v1/current.json?key={self.api_key}&q={city}&aqi=no"
        return requests.get(url).text
        #return f"Its always sunny in {city}"
         

    @tool
    def get_user_location(self, name:str) -> str:
        """Retrieve user informatoin based on user id"""
        url = f"{self.base_url}/v1/search.json?key={self.api_key}&q={name}"
        return requests.get(url).text
        #return "Chicago" 

    @tool
    def get_forecast_for_location(self, city:str) -> str:
        """Retrieves the 1 day forecast for a location"""
        url = f"{self.base_url}/v1/forecast.json?key={self.api_key}&q={city}&days=1&aqi=no&alerts=no"
        return requests.get(url).text
        #return f"Its going to be sunny and warm tomorrow in {city}"
    

