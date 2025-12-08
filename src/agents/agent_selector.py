from abc import ABC, abstractmethod
from agents.base_business_agent import BaseBusinessAgent
from config.config_models import AgentSelectorConfig
from typing import List, Optional,Dict
from utils.logger import get_logger

logger = get_logger(__name__)

class AgentSelector(ABC):
    """
    Base class AgentSelector base classes that defines the interface that is used by 
    the AgentRegistry to find the collection of registered BusinesAgents that 
    are qualified to respond to a user query
    """

    def __init__(self, seletor_name:str, config: AgentSelectorConfig):
        """
        Configures the AgentSelector
        """
        self.config = config
        self.selector_name = seletor_name
    

    @abstractmethod
    def select_agent(self, query: str, agents: Dict[str, BaseBusinessAgent]) -> Optional[BaseBusinessAgent]:
        """
        The primary Agent selection logic for the concrete AgentSelector implementation.  A conrete AgentSelector
        will process the provided query and match it to the BaseBusinessAgent that it determines
        to be the best match.  AgentSelector should select an agent only if its internal confidence score meets or 
        exceeds the min_confidence score that is set on the AgentSelectorConfig for this instance.  If an agent 
        cannot be found that meets the threshold then None is returned.  

        Args:
            query - The query to check each agent against
            agents - The list of BaseBusinessAgents to check

        Returns:
            A BaseBusinesAgent if it its match score meets or exceeds the minimum confidence threshold.  None if not
        """
        

    def shutdown(self):
        """
        Lifecycle method that is called as part of the framework shutdown process.  This method can be overridden by 
        subclasses to handle graceful shutdown/cleanup of resources
        """
        logger.debug(f"Execute shutdown for AgentSelector {self.selector_name}")