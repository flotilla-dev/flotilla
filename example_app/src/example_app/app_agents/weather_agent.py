from flotilla_langchain.agents.langchain_agent import LangChainAgent
from langchain.chat_models import BaseChatModel
from flotilla.tools.flotilla_tool import FlotillaTool
from typing import List
from flotilla.utils.logger import get_logger


logger = get_logger(__name__)


class WeatherAgent(LangChainAgent):
    """Business logic agent for return punny weather foracasts"""

    def __init__(self, llm: BaseChatModel, tools: List[FlotillaTool]):
        super().__init__(agent_name="Weather Agent", system_prompt=self.agent_prompt, llm=llm, tools=tools)

    @property
    def agent_prompt(self) -> str:
        return """
You are a weather assistant who responds with concise, helpful weather updates in a clever, lighthearted punny style.

Use weather tools for all weather information.
Never invent or guess weather conditions.
Use the location lookup tool when the location is ambiguous.

Return only a single natural-language response for the user, based only on the tool results.
        """
