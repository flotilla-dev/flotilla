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
from langchain.agents import create_agent
from agents.business_agent_response import BusinessAgentResponse, ResponseStatus, ErrorResponse

logger = get_logger(__name__)


# ------------------------------
# AgentCapability 
# ------------------------------

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
    
    DEFAULT_PROMPT = """
You are a specialized Business Agent operating inside an orchestration system.

You MUST return output strictly in the following JSON schema:

{
  "status": "success" | "error" | "warning" | "failure",
  "agent_name": "<your_agent_name>",
  "query": "<the original user query>",
  "message": "<brief summary>",
  "confidence": 0.0 to 1.0,
  "data": {},
  "actions": [],
  "errors": []
}

Rules:
- Return ONLY JSON.
- Include a confidence score between 0.0 and 1.0.
- Populate "data" with domain-specific structured content.
- If a tool is needed, call it.
"""



    def __init__(self, agent_id:str, agent_name:str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.config = None
        self.llm = None
        self._capabilities = None
        self.tools = None
        self.started = False

        
    # ------------------------------
    # Lifecycle methods
    # ------------------------------
    
    def configure(self, config:BusinessAgentConfg):
        """Lifecycle method that allows the BusinessAgent to perform necessary configuration steps after being registered with the AgentRegisry"""
        self.config = config
        self._capabilities = self._initialize_capabilities()
        self.llm = LLMFactory.get_llm(config.llm_config)
        self._process_agent_configuration()
        

    def startup(self):
        """Lifecycle method that allows BusinessAgents to perform necessary startup logic before use.  This method is called after configure()"""
        logger.debug(f"Run empty startup on Agent {self.agent_name}")
        self.create_internal_agent()
        self.started = True


    def shutdown(self):
        """Lifecycle method that allows subclasses to perform necessary cleanup"""
        logger.debug(f"Run empty shutdown on Agent {self.agent_name}")
        self.started = False


    def _process_agent_configuration(self):
        """
        Method called during configure() that allows subclasses to optionally process any additional data points that are attached to the BusinessAgentConfig
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


    def create_internal_agent(self):
        """Construct the final agent using system prompt + domain prompt + tools."""
        
        # Combine base and agent-specific instructions
        final_prompt = (
            self.DEFAULT_PROMPT
            + "\n\n"
            + self.get_agent_domain_prompt()
        )

        # Build the langchain agent
        self.agent = create_agent(
            model=self.llm,
            system_prompt=final_prompt,
            tools=self.tools
        )

    def get_agent_domain_prompt(self) -> str:
        """
        Allows simple Business Agnets to return their domain specific prompt as part of the standard internal agent creation process.  

        Returns: The prompt that is speicifc to the Agent.  This will be included with BusinessAgent default prompt which is intended to properly map LLM respones to the 
        standard response object
        """
        return ""

    # ------------------------------
    # AgentSelection helpers
    # ------------------------------
    
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
    
    # -----------------------------------------------------------------------
    # Response Builders
    # -----------------------------------------------------------------------
    def build_success_response(
        self,
        query: str,
        data: dict,
        message: str = "",
        confidence: float = 1.0,
        actions: Optional[List[Dict]] = None,
    ) -> BusinessAgentResponse:
        return BusinessAgentResponse(
            status=ResponseStatus.SUCCESS,
            agent_name=self.agent_name,
            query=query,
            confidence=confidence,
            message=message,
            data=data or {},
            actions=actions,
        )

    def build_error_response(
        self,
        query: str,
        error_code: str,
        error_details: Any,
        message: str = "",
        confidence: float = 0.0,
        actions: Optional[List[Dict]] = None,
    ) -> BusinessAgentResponse:
        return BusinessAgentResponse(
            status=ResponseStatus.ERROR,
            agent_name=self.agent_name,
            query=query,
            confidence=confidence,
            message=message or "An error occurred",
            errors=[ErrorResponse(error_code=error_code, error_details=error_details)],
            actions=actions,
            data={},
        )

    # -----------------------------------------------------------------------
    # JSON Parsing Helper
    # -----------------------------------------------------------------------
    def _parse_json_response(self, content: Any) -> dict:
        if content is None:
            return {}
        if isinstance(content, dict):
            return content
        try:
            return json.loads(content)
        except Exception:
            return {"raw_response": content}

    # -----------------------------------------------------------------------
    # Direct LLM Call Helper
    # -----------------------------------------------------------------------
    def llm_call(
        self,
        messages: list,
        query: str,
        confidence: float = 0.9,
        extract_json: bool = True,
    ) -> BusinessAgentResponse:
        try:
            result = self.llm.invoke(messages)
            content = getattr(result, "content", result)

            data = (
                self._parse_json_response(content)
                if extract_json
                else {"raw_response": content}
            )

            return self.build_success_response(
                query=query,
                data=data,
                message="LLM call succeeded",
                confidence=confidence,
            )

        except Exception as e:
            logger.exception(f"{self.agent_name} LLM call failed")
            return self.build_error_response(
                query=query,
                error_code="LLM_CALL_FAILED",
                error_details=str(e),
                message="LLM call failed",
            )

    # -----------------------------------------------------------------------
    # Internal LangChain Agent Helper
    # -----------------------------------------------------------------------
    def run_internal_agent(
        self,
        query: str,
        context: Optional[dict] = None,
        confidence: float = 0.9,
    ) -> BusinessAgentResponse:
        if not hasattr(self, "agent") or self.agent is None:
            return self.build_error_response(
                query=query,
                error_code="AGENT_NOT_INITIALIZED",
                error_details="startup() must initialize self.agent",
                message="Agent was not properly initialized.",
            )

        try:
            raw = self.agent.invoke({"input": query}, context=context)
            return self.build_success_response(
                query=query,
                data={"result": raw},
                message="Agent executed successfully.",
                confidence=confidence,
            )
        except Exception as e:
            logger.exception(f"Internal agent failed in {self.agent_name}")
            return self.build_error_response(
                query=query,
                error_code="AGENT_EXECUTION_FAILED",
                error_details=str(e),
            )
        
    def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> BusinessAgentResponse:
        """
        Execute business logic for the query
        
        Args:
            query: User query
            context: Optional context including data from other agents
            
        Returns:
            Standard response object containing the results
        """
        return self.run_internal_agent(query, context)
    


    # ------------------------------
    # Abstract methods to be implemented by subclasses 
    # ------------------------------

    @abstractmethod
    def _initialize_capabilities(self) -> List[AgentCapability]:
        """Initialize agent capabilities - must be implemented by subclasses"""
        pass


