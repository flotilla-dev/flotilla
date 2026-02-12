from app_agents.weather_agent import WeatherAgent
from langchain.chat_models import BaseChatModel
from langgraph.types import Checkpointer
from app_tools.weather_tools import WeatherTools


def weather_agent_buidler(
    llm: BaseChatModel, checkpointer: Checkpointer, weather_tools: WeatherTools
) -> WeatherAgent:
    agent = WeatherAgent(llm=llm, checkpointer=checkpointer)
    agent.attach_tools(weather_tools.get_tools())
    agent.startup()
    return agent
