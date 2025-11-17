"""
Base class for business logic agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from pydantic import BaseModel, Field
from config.config_models import BusinessAgentConfg
from llm.llm_factory import LLMFactory
from utils.logger import get_logger
from langchain_core.tools import StructuredTool

logger = get_logger(__name__)


class AgentCapability(BaseModel):
    """Describes what an agent can do"""
    name: str = Field(..., description="Capability name")
    description: str = Field(..., description="What this capability does")
    keywords: List[str] = Field(default_factory=list, description="Keywords for matching")
    examples: List[str] = Field(default_factory=list, description="Example queries")


class BaseBusinessAgent(ABC):
    """
    Abstract base class for business logic agents
    All business agents must inherit from this class
    """
    
    def __init__(self, agent_id:str, agent_name:str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.config = None
        self.llm = None
        self._capabilities = None
        self.tools = None

        
    
    def configure(self, config:BusinessAgentConfg):
        """Lifecycle method that allows the BusinessAgent to perform necessary configuration steps after being registered with the AgentRegisry"""
        self.config = config
        self._capabilities = self._initialize_capabilities()
        self.llm = LLMFactory.get_llm(config.llm_config)
        self._process_agent_configuration()
        

    def startup(self):
        """Lifecycle method that allows BusinessAgents to perform necessary startup logic before use.  This method is called after configure()"""
        logger.debug(f"Run empty startup on Agent {self.agent_name}")


    def shutdown(self):
        """Lifecycle method that allows subclasses to perform necessary cleanup"""
        logger.debug(f"Run empty shutdown on Agent {self.agent_name}")


    def _process_agent_configuration(self):
        """
        Method called during configure() that allows subclasses to optionall process any additional data points that are attached to the BusinessAgentConfig
        """
        logger.debug(f"Run empty _process_agent_configuration on Agent {self.agent_name}")


    def filter_tools(self, tool:StructuredTool) -> bool:
        """
        Called by the AgentRegistry and passed to the ToolRegistry this method allows the BusinessAgent to select which tools will be passed to the
        Agent as part of the BusinessAgentConfig.  This allows the Agent to select only the Tools that it needs from those that are 
        registered with the ToolRegistry.

        The default implementation of this method always returns True, meaning all Tools will be passed to the BusinessAgent


        Args:
            tool: A StructuredTool instance that can be checked by the BusinessAgent
        
        Returns:
            A True if the tool should be passed to the Agent, False if not
        """
        logger.debug(f"Filter tool {tool.name} for BusinessAgent {self.agent_name}")
        return True
    
    def attach_tools(self, tools:List[StructuredTool]):
        """
        Lifecycle method called by the AgentRegistry during registration that attaches the list of Tools that are available to this Agent.  The list is usually a result of 
        the tools selected via the filter_tools() method.

        Args:
            tools: The list of StructuredTool instances for this Agent
        """
        logger.debug(f"Attaching tools {tools}")
        self.tools = tools

    @abstractmethod
    def _initialize_capabilities(self) -> List[AgentCapability]:
        """Initialize agent capabilities - must be implemented by subclasses"""
        pass
    
    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Determine if this agent can handle the query
        
        Args:
            query: User query
            context: Optional context information
            
        Returns:
            Confidence score between 0.0 and 1.0
        """

        max_score = 0.0
        for capability in self._capabilities:
            score = self._match_keywords(query, capability.keywords)
            max_score = max(max_score, score)
        return max_score
    

    def get_keywords(self) -> List[str]:
        keywords = []
        for capability in self._capabilities:
            keywords.extend(capability.keywords)
        return keywords
    
    
    @abstractmethod
    def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute business logic for the query
        
        Args:
            query: User query
            context: Optional context including data from other agents
            
        Returns:
            Execution results
        """
        pass
    
    def get_capabilities(self) -> List[AgentCapability]:
        """Return list of agent capabilities"""
        return self._capabilities
    
    def get_name(self) -> str:
        """Return the name of the agent"""
        return self.agent_name
    
    def get_id(self) -> str:
        """Return the id of the agent"""
        return self.agent_id
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "capabilities": [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "keywords": cap.keywords
                }
                for cap in self._capabilities
            ]
        }
    
    def _match_keywords(self, query: str, keywords: List[str]) -> float:
        """
        Helper method to match keywords in query
        
        Returns:
            Match score between 0.0 and 1.0
        """
        query_lower = query.lower()
        matches = sum(1 for keyword in keywords if keyword.lower() in query_lower)
        return min(matches / max(len(keywords), 1), 1.0) if keywords else 0.0
    
    def _create_result(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Helper method to create standardized result"""
        result = {
            "success": success,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "timestamp": datetime.now().isoformat()
        }
        
        if data is not None:
            result["data"] = data
        if error:
            result["error"] = error
        if metadata:
            result["metadata"] = metadata
        
        return result
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_response": content}