
from flotilla.container.flotilla_container import FlotillaContainer
from example_app.src.app_agents.weather_agent import WeatherAgent
from typing import Optional, Dict
from langchain.chat_models import BaseChatModel
from langgraph.types import Checkpointer

def weather_agent_buidler(container:FlotillaContainer, config:Optional[Dict], llm:BaseChatModel, checkpointer:Checkpointer) -> WeatherAgent:
    return WeatherAgent()