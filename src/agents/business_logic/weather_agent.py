from agents.base_business_agent import (
    BaseBusinessAgent,
    BusinessDomain,
    AgentCapability
)
from typing import Any, Dict, Optional
from llm.llm_provider import LLMProvider,LLMConfig
from langchain_core.messages import HumanMessage, SystemMessage
from utils.logger import get_logger


logger = get_logger(__name__)


class WeatherAgent(BaseBusinessAgent):
    """Business logic agent for return punny weather foracasts"""

    def __init__(self, llm_config:LLMConfig | None = None):
        super().__init__("weather_agent", "Weather Pun Agent", llm_config)


    def _initialize_capabilities(self):
        capabilities = [
            AgentCapability(
                name="Forecast",
                description="Creates a forecast for the city in a pun",
                keywords=["weather", "forecast"],
                examples=[
                    "What is the weather like in Chicago?",
                    "What is the forceast for NYC?"                ]
            )]
        return capabilities
        
    
    def get_domain(self) -> BusinessDomain:
        return BusinessDomain.WEATHER
    
    def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        system_prompt="""You are an expert weather forecaster, who speaks in puns.

        You have access to two tools:

        - get_weather_for_location: use this to get the weather for a specific location
        - get_user_location: use this to get the user's location

        If a user asks you for the weather, make sure you know the location. If you can tell from the question that they mean wherever they are, use the get_user_location tool to find their location.
        
        Provide the results in structured JSON format """

        user_prompt=f"Query: {query}"
        logger.info(f"Type of self.llm: {type(self.llm)}")
        logger.info(f"Calling LLM to get punny weather for query {user_prompt}")
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)        
        ])
        
        return self._parse_json_response(response.content)
        
