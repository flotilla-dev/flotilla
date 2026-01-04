
from typing import Dict, Any, List, Optional

from langchain_core.tools import StructuredTool

from flotilla.agents.base_business_agent import BaseBusinessAgent, ToolDependency
from flotilla.agents.business_agent_response import BusinessAgentResponse, ErrorResponse, ResponseStatus
from flotilla.agents.agent_selector import AgentSelector
from flotilla.agents.response_factory import ResponseFactory
from flotilla.tools.tool_registry import ToolRegistry
from flotilla.flotilla_configuration_error import FlotillaConfigurationError
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)

class BusinessAgentRegistry:
    """
    Registry for managing and selecting business logic agents
    Dynamically routes queries to the most appropriate agent based on content
    """
    
    def __init__(self, *, agents:Dict[str, BaseBusinessAgent], tool_registry:ToolRegistry, agent_selector:AgentSelector):
        self._agents:Dict[str, BaseBusinessAgent] = agents
        self._agent_selector:AgentSelector = agent_selector
        self._tool_registry:ToolRegistry = tool_registry


    def start(self):
        """
        Runs the startup process on the AgentRegistry.  The default behavior is for 
        the AgnetRegistry to iterate through all BusinessAgents and attach 
        all available ToolProviders to the agent and then call startup()
        on the agent
        """
        logger.info("Start processing BusinessAgents to attach Tools")
        
        for agent in self._agents.values():
            logger.info(f"Startup BusinessAgent {agent.get_name()}")
            if (agent):
                # get the dependencies for the Agent
                dependencies:List[ToolDependency] = agent.get_tool_dependencis()
                tools:List[StructuredTool] = []
                for dependecy in dependencies:
                    tool:StructuredTool = self._tool_registry.get_tool_by_name(dependecy.tool_name)
                    if tool:
                        logger.info(f"Attach tool {dependecy.tool_name} to Agent {agent.agent_name}")
                        tools.append(tool)
                    elif dependecy.required:
                        raise FlotillaConfigurationError(f"Agent {agent.get_name} requires Tool {dependecy.tool_name} and it is not available in the ToolRegistry")
                    else:
                        logger.warn(f"Agent {agent.get_name} requests optinal Tool {dependecy.tool_name} and it is not available in the ToolRegistry")
                
                agent.attach_tools(tools=tools)
                agent.startup()

        logger.info("Finished  processing BusinessAgents")


    def get_agent(self, agent_id: str) -> Optional[BaseBusinessAgent]:
        """Get agent by ID"""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents with their capabilities"""
        return [agent.get_info() for agent in self._agents.values()]
    
    def list_agent_names(self) ->List[str]:
        """List the name of all registered agents"""
        return [agent.agent_name for agent in self._agents.values()]
    
    def select_agent(
        self,
        query: str
        ) -> Optional[BaseBusinessAgent]:
        """
        Select the most appropriate agent for a query.  This method will leverage the AgentSelector that 
        was created during startup to select the best agent that meets the minimum confidence score.  If 
        an agent cannot be found that meets the criteria then None is returned
        
        Args:
            query: User query
            context: Optional context information
            
        Returns:
            Selected agent or None if no suitable agent found
        """
        if not self._agents:
            logger.warning("No agents registered")
            return None
 
        return self._agent_selector.select_agent(query=query, agents=self._agents)
    
    
    
    def execute_with_best_agent(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
        ) -> BusinessAgentResponse:
        """
        Select and execute with the best agent for the query
        
        Args:
            query: User query
            context: Optional context
            min_confidence: Minimum confidence threshold
            
        Returns:
            Execution results including agent selection info
        """
        # Select agent
        selected_agent = self.select_agent(query=query)
        
        if not selected_agent:
            return ResponseFactory.build_error_response(
                status=ResponseStatus.NO_VALID_AGENT,
                query=query,
                agent_name="",
                message="No suitable business logic agent found for this query",
                errors=[ErrorResponse(error_code="NO_VALID_AGENT", error_details="There are no valid agents for the user query")]
            )
        
        # Execute with selected agent
        logger.info(f"Executing query with agent: {selected_agent.agent_name}")
        return selected_agent.execute(query, context)
    

    def shutdown(self):
        """
        Lifecycle method that is called by OrchestrationAgent to safely shutdown the AgentRegistry.  The AgentRegistry will cycle through all registered BusinessAgents and call their
        shutdown methods to allow for safe cleanup
        """
        logger.info("Shutdown called for AgentRegistry, shutdown all registered Agents")
        
        for agent in self._agents.values():
            if (agent):
                logger.info(f"Shutdown BusinessAgent {agent.agent_name}")
                agent.shutdown() 