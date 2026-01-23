from app_tools.weather_tools import WeatherTools
from flotilla.core.errors import FlotillaConfigurationError

def weather_tools_builder(api_key:str, base_url:str, use_api:bool = True) -> WeatherTools:
    if not api_key:
        raise FlotillaConfigurationError("Required key 'api_key' does not exist for WeatherTools")
    if not base_url:
        raise FlotillaConfigurationError("Required key 'base_url' does not exist for WeatherTools")

    return WeatherTools(api_key=api_key, base_url=base_url, use_api=use_api)

    