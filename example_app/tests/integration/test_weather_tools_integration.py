import pytest

from example_app.src.app_tools.weather_tools import WeatherTools

'''
@pytest.mark.integration
def test_weather_tools_integration():
    settings = ConfigLoader.load("UAT", "example_app/src/config")

    config = ConfigFactory.create_tool_config("weather_tools", settings)
    assert config is not None

    tool = WeatherTools()
    tool.configure(config)


    location_tool = tool.get_tool("get_user_location")
    location = location_tool.run({"name": "Chicago"})
    assert "Chicago" in location

    current_tool = tool.get_tool("get_weather_for_location")
    current = current_tool.run({"city": "Chicago"})
    assert "Chicago" in current

    forecast_tool = tool.get_tool("get_forecast_for_location")
    forecast = forecast_tool.run({"city": "Chicago"})
    assert "Chicago" in forecast


def test_feature_flag_use():
    settings = ConfigLoader.load("UAT", "example_app/src/config")

    config = ConfigFactory.create_tool_config("weather_tools", settings)
    assert config is not None

    assert config.feature_flags.get("weather_tools").get("use_api")
    # now change the feature flag in config to false before passign to the tool

    config.feature_flags.get("weather_tools")["use_api"] = False
    assert not config.feature_flags.get("weather_tools").get("use_api")

    tool = WeatherTools()
    tool.configure(config)


    location_tool = tool.get_tool("get_user_location")
    location = location_tool.run({"name": "Den"})
    assert "Denver" in location

    current_tool = tool.get_tool("get_weather_for_location")
    current = current_tool.run({"city": "Chicago"})
    assert "Its always sunny in" in current

    forecast_tool = tool.get_tool("get_forecast_for_location")
    forecast = forecast_tool.run({"city": "Chicago"})
    assert "Its going to be sunny and warm tomorrow in " in forecast
'''
