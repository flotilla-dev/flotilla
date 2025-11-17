from agents.base_business_agent import BaseBusinessAgent, AgentCapability
from utils.logger import get_logger
from config.config_models import LLMConfig
from typing import Any, Dict, Optional, List


logger = get_logger(__name__)

class TestAgent(BaseBusinessAgent):

    def __init__(self):
        super().__init__(agent_id="test_agent_1", agent_name= "Test Agent_1")

    def _initialize_capabilities(self) -> List[AgentCapability]:
        capabilities = [
            AgentCapability(
                name="Forecast",
                description="Creates a forecast for the city in a pun",
                keywords=["weather", "forecast"],
                examples=[
                    "What is the weather like in Chicago?",
                    "What is the forceast for NYC?"                ]
            )
        ]
        return capabilities
    
    def can_handle(self, query, context = None):
        return self._match_keywords(query, self.get_keywords())
    
    def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass
    