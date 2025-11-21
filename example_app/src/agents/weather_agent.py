from agents.base_business_agent import (
    BaseBusinessAgent,
    AgentCapability
)
from utils.logger import get_logger



logger = get_logger(__name__)
   

class WeatherAgent(BaseBusinessAgent):
    """Business logic agent for return punny weather foracasts"""

    def __init__(self):
        super().__init__("weather_agent", "Weather Pun Agent")


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
    
    def get_agent_domain_prompt(self):
        return """You are an expert weather forecaster, who speaks in puns.

        You have access to two tools:

        - get_weather_for_location: use this to get the weather for a specific location
        - get_user_location: use this to get the user's location

        If a user asks you for the weather, make sure you know the location. If you can tell from the question that they mean wherever they are, use the get_user_location tool to find their location.
        
        Provide the results in structured JSON format """
    
