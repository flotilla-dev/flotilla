from langchain.chat_models import BaseChatModel
from example_apps.weather.src.weather.app_agents.weather_agent import WeatherAgent
from flotilla.tools.flotilla_tool import FlotillaTool
from typing import List


def weather_agent_provider(llm: BaseChatModel, tools: List[FlotillaTool]) -> WeatherAgent:
    return WeatherAgent(llm=llm, tools=tools)
