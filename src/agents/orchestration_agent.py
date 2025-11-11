"""
Main Orchestration Agent
Coordinates tools, business logic, decisioning agent and actions
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain.agents import create_agent
from langgraph.types import Checkpointer
from langgraph.checkpoint.memory import InMemorySaver

from config.config_models import OrchestrationConfig
from agents.agent_registry import BusinessAgentRegistry
from utils.logger import get_logger
from llm.llm_factory import LLMFactory
from tools.tool_registry import ToolRegistry


logger = get_logger(__name__)


class OrchestrationAgent:
    """
    Main orchestration agent 
    """
    
    def __init__(self, config: OrchestrationConfig):
        self.config = config
        
        #TODO define a structure for creation and initialization of all tools & agents 
        
        # load the LLM Provider
        self.llm_factory = LLMFactory()
        self.llm = self.llm_factory.get_llm(config.llm_config) 

        # load the tools
        #self.checkpointer = self._create_checkpointer()
        self.tool_registry = ToolRegistry()
        self.tools = self.tool_registry.get_all_tools()

        logger.info(f"Loaded {len(self.tools)} from from ToolRegistry")

        # load the agents
        self.business_registry = BusinessAgentRegistry()
        logger.info(f"Registered {len(self.business_registry.agents)} with AgentRegistry")
        
        logger.info(f"Orchestration agent initialized for client: {config.client.client_name}")
    

    
    def _create_checkpointer(self) -> Checkpointer:
        checkpointer = InMemorySaver()
        return checkpointer
    

    
    def execute(self, query: str) -> Dict[str, Any]:
        """
        Execute an orchestration query
        
        Args:
            query: Natural language query or command
            
        Returns:
            Execution results
        """
        logger.info(f"Executing orchestration query: {query}")

        try:
            return self.business_registry.execute_with_best_agent(query=query)
    
        except Exception as e:
            logger.error(f"Orchestration execution failed: {e}")
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up orchestration agent resources")
    