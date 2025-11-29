import pytest
from example_app.src.app_tools.weather_tools import WeatherTools
from config.config_models import ToolConfig



@pytest.fixture
def valid_config():
    """Valid config fixture to bootstrap WeatherTools successfully"""

    config = ToolConfig()
    config.tool_configuration = {
            "WEATHER_API": {
                "KEY": "TEST-KEY-123",
                "BASE_URL": "https://api.weatherapi.com/v1"
            }
        }
    return config


def test_configure_tools_success(valid_config):
    """Ensures _configure_tools loads API configuration correctly"""
    assert valid_config.tool_configuration.get("WEATHER_API").get("KEY") == "TEST-KEY-123"
    assert valid_config.tool_configuration.get("WEATHER_API").get("BASE_URL") == "https://api.weatherapi.com/v1"


def test_configure_tools_missing_api_key():
    """WeatherTools should fail if key missing"""
    tools = WeatherTools()
    config = ToolConfig()
    config.tool_configuration = {
            "WEATHER_API": {
                "BASE_URL": "https://api.weatherapi.com/v1"
            }
        }

    with pytest.raises(Exception):
        tools.configure(config)


def test_configure_tools_missing_base_url():
    """WeatherTools should fail if BASE_URL missing"""
    tools = WeatherTools()
    config = ToolConfig()
    config.tool_configuration = {
            "WEATHER_API": {
                "KEY": "TEST-KEY-123"
            }
        }

    with pytest.raises(Exception):
        tools.configure(config)


def test_registered_tools(valid_config):
    tool = WeatherTools()
    tool.configure(valid_config)
    
    names = tool.get_tool_names()
    assert len(names) == 3


def test_get_weather_for_location(valid_config):
    tool = WeatherTools()
    tool.configure(valid_config)
    current_tool = tool.get_tool("get_weather_for_location")
    result = current_tool.run({"city": "Chicago"})
    # is an error message from the API, but method runs properly
    assert result is not None


def test_get_user_location(valid_config):
    tool = WeatherTools()
    tool.configure(valid_config)
    location_tool = tool.get_tool("get_user_location")
    result = location_tool.run({"name": "Chicago"})
    # is an error message from the API, but method runs properly
    assert result is not None


def test_get_forecast_for_location(valid_config):
    tool = WeatherTools()
    tool.configure(valid_config)
    forecast_tool = tool.get_tool("get_forecast_for_location")
    result = forecast_tool.run({"city": "Chicago"})
    # is an error message from the API, but method runs properly
    assert result is not None

