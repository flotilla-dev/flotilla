from app_agents.weather_agent import WeatherAgent
from langchain.chat_models import BaseChatModel
from langgraph.types import Checkpointer

def weather_agent_buidler(llm:BaseChatModel, checkpointer:Checkpointer) -> WeatherAgent:
    return WeatherAgent(llm=llm, checkpointer=checkpointer)