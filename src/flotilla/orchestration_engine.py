"""
Main Orchestration Agent
Coordinates tools, business logic, decisioning agent and actions
"""
from typing import Dict

from flotilla.agents.agent_registry import BusinessAgentRegistry
from flotilla.agents.response_factory import ResponseFactory
from flotilla.agents.business_agent_response import BusinessAgentResponse, ErrorResponse, ResponseStatus
from flotilla.utils.logger import get_logger
from flotilla.tools.tool_registry import ToolRegistry


logger = get_logger(__name__)


class OrchestrationEngine:
    """
    Main orchestration engine 
    """
    
    def __init__(self, *, agent_registry:BusinessAgentRegistry, tool_registry:ToolRegistry):
        logger.info("*** OrchestrationEngine starting startup ***")
        self._tool_registry = tool_registry
        self._agent_registry = agent_registry
        self._agent_registry.start()
        self.running:bool = True
        logger.info("*** OrchestrationEngine finished startup ***")
    



    
    def execute(self, query: str, context:Dict) -> BusinessAgentResponse:
        """
        Execute an orchestration query
        
        Args:
            query: Natural language query or command
            
        Returns:
            Execution results
        """
        #TODO: Change the method signature to support context and config 
        logger.debug(f"Executing orchestration query: {query}")

        try:
            return self._agent_registry.execute_with_best_agent(query=query, context=context)
    
        except Exception as e:
            logger.error(f"Orchestration execution failed: {e}")
            return ResponseFactory.build_error_response(
                status=ResponseStatus.INTERNAL_ERROR,
                query=query,
                agent_name="Unknown",
                message="Error executing business agent",
                errors=[ErrorResponse(error_code="AGENT_EXECUTION_FAILED", error_details=str(e))]
            )
            
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up orchestration engine resources")
        if self.running:
            self._tool_registry.shutdown()
            self._agent_registry.shutdown()
            self.running = False

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._tool_registry
    
    @property
    def agent_registry(self) -> BusinessAgentRegistry:
        return self._agent_registry
    