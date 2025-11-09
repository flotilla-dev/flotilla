"""
Base class for business logic agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import json

from pydantic import BaseModel, Field
from config.config_models import LLMConfig
from config.settings import Settings
from llm.llm_provider import LLMProvider


class BusinessDomain(str, Enum):
    """Business domains for agent specialization"""
    PRICING = "pricing"
    INVENTORY = "inventory"
    CUSTOMER = "customer"
    SALES = "sales"
    MARKETING = "marketing"
    FINANCE = "finance"
    OPERATIONS = "operations"
    WEATHER = "weather"


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
    
    def __init__(self, agent_id: str, agent_name: str, llm_config:LLMConfig | None = None):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self._capabilities = self._initialize_capabilities()
        if (llm_config is None):
            settings = Settings()
            self.llm_config = settings.get_llm_config()
        else:
            self.llm_config = llm_config
        llm_proivder = LLMProvider()
        self.llm = llm_proivder.get_llm(llm_config)
        
    
    @abstractmethod
    def _initialize_capabilities(self) -> List[AgentCapability]:
        """Initialize agent capabilities - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def get_domain(self) -> BusinessDomain:
        """Return the business domain this agent specializes in"""
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
            "domain": self.get_domain().value,
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
            "domain": self.get_domain().value,
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