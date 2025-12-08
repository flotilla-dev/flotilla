"""
Business Agent Registry
Manages and routes queries to appropriate business logic agents
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from agents.base_business_agent import BaseBusinessAgent
from agents.agent_selector import AgentSelector
from agents.agent_selector_factory import AgentSelectorFactory
from llm.llm_factory import LLMFactory
from config.config_models import AgentRegistryConfig
from config.config_factory import ConfigFactory
from utils.logger import get_logger
from tools.tool_registry import ToolRegistry
from agents.business_agent_response import BusinessAgentResponse,ResponseStatus,ErrorResponse
from agents.response_factory import ResponseFactory

import importlib
import inspect
import pkgutil
import pathlib

logger = get_logger(__name__)


class BusinessAgentRegistry:
    """
    Registry for managing and selecting business logic agents
    Dynamically routes queries to the most appropriate agent based on content
    """
    
    def __init__(self, config:AgentRegistryConfig, tool_registry:ToolRegistry):       
        self.config = config
        self.tool_registry = tool_registry
        
        self.llm = LLMFactory.get_llm(self.config.llm_config)
        self.agent_selector: AgentSelector = AgentSelectorFactory.create_agent_selector(self.config.agent_selector_config)
        self.agents: Dict[str, BaseBusinessAgent] = {}
        if (self.config.agent_discovery):
            self._discover_agents()
 
    
    def _discover_agents(self):
        """Internal: scans configured packages and loads BaseBusinessAgent objects."""
        for package_name in self.config.agent_packages:
            package = importlib.import_module(package_name)
            package_path = pathlib.Path(package.__file__).parent

            iterator = (
                pkgutil.walk_packages([str(package_path)], f"{package_name}.")
                if self.config.agent_recursive
                else pkgutil.iter_modules([str(package_path)])
            )

            # Scan submodules
            for _, full_module_name, is_pkg in iterator:
                if not is_pkg:
                    self._load_agents_from_module(full_module_name)

            # Also check the package’s __init__.py
            self._load_agents_from_module(package_name)



    def _load_agents_from_module(self, module_name: str):
        """Import a module and load all BaseBusinessAgent subclasses inside it."""
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            logger.warning(f"Skipping {module_name}: import failed ({e})")
            return

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseBusinessAgent) and obj is not BaseBusinessAgent:
                try:
                    agent_instance = obj()
                    self.register_agent(agent_instance)
                except Exception as e:
                    logger.error(f"Failed to initialize agent {obj.__name__}: {e}")



    
    def register_agent(self, agent: BaseBusinessAgent):
        """
        Register a new business agent
        
        Args:
            agent: Business agent instance
        """
        logger.info(f"Registering agent: {agent.agent_name} (ID: {agent.agent_id}")
        try:
            # 1) Greate the Agent speficic BusinessAgnetConfig for this instance and call configure()
            agent_config = ConfigFactory.create_business_agent_config(agent.agent_name, self.config.settings)
            agent.configure(agent_config)
            # 2) filter and attach tools to the Agent
            tools = self.tool_registry.get_tools(agent.filter_tools)
            agent.attach_tools(tools)
            # 3) Start the agent
            agent.startup()
            # 4) Add agent to the internal map of Agents 
            self.agents[agent.agent_id] = agent
        except Exception as e:
            logger.error(f"Error registering Agent {agent.agent_name}: {e}")
        
    
    def unregister_agent(self, agent_id: str):
        """
        Unregister a business agent
        
        Args:
            agent_id: Agent ID to remove
        """
        logger.info(f"Attempting to unregister agent: {agent_id}")
        if agent_id in self.agents:
            agent = self.agents.pop(agent_id)
            agent.shutdown()

    
    def get_agent(self, agent_id: str) -> Optional[BaseBusinessAgent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents with their capabilities"""
        return [agent.get_info() for agent in self.agents.values()]
    
    def list_agent_names(self) ->List[str]:
        """List the name of all registered agents"""
        return [agent.agent_name for agent in self.agents.values()]
    
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
        if not self.agents:
            logger.warning("No agents registered")
            return None
        # Convert dict values to list for selector
        agents_list = list(self.agents.values())
        return self.agent_selector.select_agent(query, agents_list)
    
    
    
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
        agent_names = self.list_agent_names()
        
        for name in agent_names:
            logger.debug(f"Shutdown BusinessAgent {name}")
            agent = self.get_agent(name)
            if (agent):
                agent.shutdown()