from abc import ABC, abstractmethod
from flotilla.agents.base_business_agent import BaseBusinessAgent
from flotilla.core.agent_input import AgentInput
from typing import Optional,Dict
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)

class AgentSelector(ABC):
    """
    Base class AgentSelector base classes that defines the interface that is used by 
    the AgentRegistry to find the collection of registered BusinesAgents that 
    are qualified to respond to a user query
    """

    def __init__(self, *, selector_name:str, min_confidence:float):
        """
        Configures the AgentSelector

        Args:
            selector_name - The name of the selector
            min_confidence - The minimum confidecne score needed by the AgentSelector
        """
        self.min_confidence = min_confidence
        self.selector_name = selector_name
    

    @abstractmethod
    def select_agent(self, agent_input:AgentInput, agents: Dict[str, BaseBusinessAgent]) -> Optional[BaseBusinessAgent]:
        """
        The primary Agent selection logic for the concrete AgentSelector implementation.  A conrete AgentSelector
        will process the provided query and match it to the BaseBusinessAgent that it determines
        to be the best match.  AgentSelector should select an agent only if its internal confidence score meets or 
        exceeds the min_confidence score that is set on the AgentSelectorConfig for this instance.  If an agent 
        cannot be found that meets the threshold then None is returned.  

        Args:
            agent_input - The full input from the user 
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