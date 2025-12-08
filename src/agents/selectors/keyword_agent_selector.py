from agents.agent_selector import AgentSelector
from agents.base_business_agent import BaseBusinessAgent
from config.config_models import KeywordAgentSelectorConfig
from typing import Optional, List, Dict

class KeywordAgentSelector(AgentSelector):

    def __init__(self, config:KeywordAgentSelectorConfig):
        super().__init__("KeywordAgentSelector", config)

    def select_agent(self, query:str, agents:Dict[str, BaseBusinessAgent]) -> Optional[BaseBusinessAgent]:
        """
        Concrete AgentSelector that matches the keywords for each agent against the query
        """
        max_score = -1.0
        selected_agent = None

        for agent in agents.values():
            capabilities = agent.get_capabilities()
            for capability in capabilities:
                score = self._match_keywords(query, capability.keywords)
                if score > max_score and score >= self.config.min_confidence:
                    max_score = score
                    selected_agent = agent
        
        return selected_agent


    def _match_keywords(self, query: str, keywords: List[str]) -> float:
        """
        Helper method to match keywords in query
        
        Returns:
            Match score between 0.0 and 1.0
        """
        query_lower = query.lower()
        matches = sum(1 for keyword in keywords if keyword.lower() in query_lower)
        return min(matches / max(len(keywords), 1), 1.0) if keywords else 0.0 