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
from flotilla.agents.agent_input import AgentInput
from flotilla.agents.execution_config import ExecutionConfig


logger = get_logger(__name__)


class FlotillaRuntime:
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
    


    def run(self, query: str, *, 
            user_id: str | None = None, 
            thread_id: str | None = None, 
            request_id:str | None = None,
            metadata: dict | None = None) -> BusinessAgentResponse:
        # build the context for the query

        input = AgentInput(
            query=query,
            user_id=user_id,
            thread_id=thread_id,
            metadata=metadata
        )

        config = ExecutionConfig(
            thread_id=thread_id,
            trace_id=request_id
        )

        # Select agent
        selected_agent = self.agent_registry.select_agent(agent_input=input)
        
        if not selected_agent:
            return ResponseFactory.build_error_response(
                status=ResponseStatus.NO_VALID_AGENT,
                query=query,
                agent_name="",
                message="No suitable business logic agent found for this query",
                errors=[ErrorResponse(error_code="NO_VALID_AGENT", error_details="There are no valid agents for the user query")]
            )
        
        # Execute with selected agent
        logger.info(f"Executing query {query} with agent: {selected_agent.agent_name}")
        return selected_agent.run(agent_input=input, config=config)

            
    
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
    