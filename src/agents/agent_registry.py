"""
Business Agent Registry
Manages and routes queries to appropriate business logic agents
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from agents.base_business_agent import BaseBusinessAgent
from llm.llm_factory import LLMFactory
from config.config_models import AgentRegistryConfig
from utils.logger import get_logger

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
    
    def __init__(self, config:AgentRegistryConfig):       
        self.config = config
        
        self.llm = LLMFactory.get_llm(self.config.llm_config)
        self.agents: Dict[str, BaseBusinessAgent] = {}
        if (self.config.agent_discovery):
            self.agents = self._discover_agents()
 
    
    def _discover_agents(self) -> Dict[str, BaseBusinessAgent]:
        """Internal: scans configured packages and loads BaseBusinessAgent objects."""
        all_agents = {}

        for package_name in self.config.agent_packages:
            package = importlib.import_module(package_name)
            package_path = pathlib.Path(package.__file__).parent

            iterator = (
                pkgutil.walk_packages([str(package_path)], f"{package_name}.")
                if self.config.agent_recursive
                else pkgutil.iter_modules([str(package_path)])
            )

            for _, full_module_name, is_pkg in iterator:
                if is_pkg:
                    continue

                try:
                    module = importlib.import_module(full_module_name)
                except Exception as e:
                    print(f"Skipping {full_module_name}: import failed ({e})")
                    continue

                for _, obj in inspect.getmembers(module, inspect.isclass):
                    # Look for subclasses of BaseBusinessAgent (not the base class itself)
                    if issubclass(obj, BaseBusinessAgent) and obj is not BaseBusinessAgent:
                        try:
                            agent_instance = obj()
                            all_agents[agent_instance.agent_id] = agent_instance
                        except Exception as e:
                            logger.error(f"Failed to initialize agent {obj.__name__}: {e}")

        # Also check classes defined directly in the package’s __init__.py
        for package_name in self.config.agent_packages:
            package = importlib.import_module(package_name)
            for _, obj in inspect.getmembers(package, inspect.isclass):
                if issubclass(obj, BaseBusinessAgent) and obj is not BaseBusinessAgent:
                    try:
                        agent_instance = obj()
                        all_agents[agent_instance.agent_id] = agent_instance
                    except Exception as e:
                        logger.error(f"Failed to initialize agent {obj.__name__}: {e}")

        return all_agents

    
    def register_agent(self, agent: BaseBusinessAgent):
        """
        Register a new business agent
        
        Args:
            agent: Business agent instance
        """
        self.agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.agent_name} (ID: {agent.agent_id}")
    
    def unregister_agent(self, agent_id: str):
        """
        Unregister a business agent
        
        Args:
            agent_id: Agent ID to remove
        """
        if agent_id in self.agents:
            agent = self.agents.pop(agent_id)
            logger.info(f"Unregistered agent: {agent.agent_name}")
    
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
        query: str,
        context: Optional[Dict[str, Any]] = None,
        use_llm_router: bool = True,
        min_confidence: float = 0.3
    ) -> Optional[BaseBusinessAgent]:
        """
        Select the most appropriate agent for a query
        
        Args:
            query: User query
            context: Optional context information
            use_llm_router: Whether to use LLM for routing (fallback to keyword matching)
            min_confidence: Minimum confidence threshold
            
        Returns:
            Selected agent or None if no suitable agent found
        """
        if not self.agents:
            logger.warning("No agents registered")
            return None
        
        # Method 1: Use keyword-based confidence scores from agents
        agent_scores = {}
        for agent_id, agent in self.agents.items():
            score = agent.can_handle(query, context)
            agent_scores[agent_id] = score
        
        # Get best agent from keyword matching
        best_keyword_agent_id = max(agent_scores, key=agent_scores.get)
        best_keyword_score = agent_scores[best_keyword_agent_id]
        
        logger.info(f"Keyword-based scores: {agent_scores}")
        
        # Method 2: Use LLM for intelligent routing
        if use_llm_router and len(self.agents) > 1:
            llm_selected_agent_id = self._llm_select_agent(query, context)
            
            if llm_selected_agent_id and llm_selected_agent_id in self.agents:
                # If LLM selected an agent with reasonable keyword score, use it
                if agent_scores.get(llm_selected_agent_id, 0) >= min_confidence * 0.5:
                    logger.info(f"LLM selected agent: {llm_selected_agent_id}")
                    return self.agents[llm_selected_agent_id]
        
        # Fallback to keyword-based selection
        if best_keyword_score >= min_confidence:
            logger.info(f"Selected agent based on keywords: {best_keyword_agent_id} (score: {best_keyword_score})")
            return self.agents[best_keyword_agent_id]
        
        logger.warning(f"No agent met confidence threshold. Best score: {best_keyword_score}")
        return None
    
    def _llm_select_agent(self, query: str, context: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Use LLM to intelligently select the best agent
        
        Returns:
            Agent ID or None
        """
        # Build agent descriptions
        agent_descriptions = []
        for agent_id, agent in self.agents.items():
            capabilities = "\n".join([
                f"  - {cap.name}: {cap.description}"
                for cap in agent.get_capabilities()
            ])
            agent_descriptions.append(
                f"Agent ID: {agent_id}\n"
                f"Name: {agent.agent_name}\n"
                f"Capabilities:\n{capabilities}"
            )
        
        system_prompt = """You are an intelligent query router. Based on the user query and available agents, 
        select the MOST APPROPRIATE agent to handle the request. Consider the query intent, keywords, and 
        which agent's capabilities best match the user's needs.
        
        Respond with ONLY the agent ID, nothing else."""
        
        user_prompt = f"""
        User Query: {query}
        
        {f"Context: {context}" if context else ""}
        
        Available Agents:
        {chr(10).join(agent_descriptions)}
        
        Select the best agent ID:
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            selected_id = response.content.strip()
            
            # Validate the response is a known agent ID
            if selected_id in self.agents:
                return selected_id
            else:
                logger.warning(f"LLM returned unknown agent ID: {selected_id}")
                return None
                
        except Exception as e:
            logger.error(f"LLM agent selection failed: {e}")
            return None
    
    def execute_with_best_agent(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        min_confidence: float = 0.3
    ) -> Dict[str, Any]:
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
        selected_agent = self.select_agent(query, context, min_confidence=min_confidence)
        
        if not selected_agent:
            return {
                "success": False,
                "error": "No suitable business logic agent found for this query",
                "available_agents": [agent.agent_name for agent in self.agents.values()],
                "timestamp": datetime.now().isoformat()
            }
        
        # Execute with selected agent
        logger.info(f"Executing query with agent: {selected_agent.agent_name}")
        result = selected_agent.execute(query, context)
        
        # Add selection metadata
        result["selected_agent"] = selected_agent.agent_name
        result["selection_timestamp"] = datetime.now().isoformat()
        
        return result
    
    def execute_with_multiple_agents(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        min_confidence: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Execute query with all agents that meet confidence threshold
        Useful for getting multiple perspectives
        
        Args:
            query: User query
            context: Optional context
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of results from all qualifying agents
        """
        results = []
        
        for agent_id, agent in self.agents.items():
            confidence = agent.can_handle(query, context)
            
            if confidence >= min_confidence:
                logger.info(f"Executing with {agent.agent_name} (confidence: {confidence})")
                result = agent.execute(query, context)
                result["confidence"] = confidence
                results.append(result)
        
        return results
    