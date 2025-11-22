"""
Tests for base business agent
"""
import pytest
from datetime import datetime

from agents.base_business_agent import (
    BaseBusinessAgent,
    AgentCapability
)

from unittest.mock import Mock, MagicMock, patch


from agents.business_agent_response import (
    BusinessAgentResponse, 
    ErrorResponse,
    ResponseStatus
)

from config.config_models import LLMConfig

from typing import List

import json


class ConcreteBusinessAgent(BaseBusinessAgent):
    """Concrete implementation for testing"""
    
    def __init__(self, agent_id:str, agent_name:str):
        self.test_keywords = ["test", "sample"]
        super().__init__(agent_id=agent_id, agent_name=agent_name)
        
    
    def _initialize_capabilities(self) ->List[AgentCapability]:
        capabilities = [
            AgentCapability(
                name="test_capability",
                description="Test capability description",
                keywords=self.test_keywords,
                examples=["test query", "sample query"]
            )
        ]
        return capabilities
    
    def can_handle(self, query, context=None):
        return self._match_keywords(query, self.test_keywords)
    
    def execute(self, query, context=None):
        return self._create_result(
            success=True,
            data={"executed": True, "query": query}
        )


@pytest.mark.unit
class TestAgentCapability:
    """Test AgentCapability model"""
    
    def test_create_capability(self):
        """Test creating capability"""
        capability = AgentCapability(
            name="test_cap",
            description="Test description",
            keywords=["key1", "key2"],
            examples=["example 1"]
        )
        
        assert capability.name == "test_cap"
        assert capability.description == "Test description"
        assert capability.keywords == ["key1", "key2"]
        assert capability.examples == ["example 1"]
    
    def test_capability_defaults(self):
        """Test capability default values"""
        capability = AgentCapability(
            name="test",
            description="desc"
        )
        
        assert capability.keywords == []
        assert capability.examples == []


@pytest.mark.unit
class TestBaseBusinessAgent:
    """Test base business agent functionality"""
    
    def test_initialization(self):
        """Test agent initializes correctly"""
        agent = ConcreteBusinessAgent(
            agent_id="test_id",
            agent_name="Test Name"        
            )
        
        assert agent.agent_id == "test_id"
        assert agent.agent_name == "Test Name"
        assert agent._capabilities is None
        assert agent.config is None
        assert agent.llm is None

    def test_configure(self, mock_business_agent_config):
        """Test the cofigure() lifecycle call"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")
        agent.configure(mock_business_agent_config)

        assert agent.agent_id == "test_id"
        assert agent.agent_name == "Test Agent"
        assert agent._capabilities is not None
        assert agent.config is not None
        assert agent.llm is not None



    def test_startup(self, mock_settings):
        pass

    def test_shutdown(self, mock_settings):
        pass
    
    def test_get_capabilities(self, mock_business_agent_config):
        """Test retrieving agent capabilities"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")

        agent.configure(mock_business_agent_config)
        capabilities = agent.get_capabilities()
        
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert all(isinstance(cap, AgentCapability) for cap in capabilities)
    
    def test_get_info(self, mock_business_agent_config):
        """Test getting agent information"""
        agent = ConcreteBusinessAgent(
            agent_id="test_id",
            agent_name="Test Agent"
            )
        agent.configure(mock_business_agent_config)
        
        info = agent.get_info()
        
        assert info["agent_id"] == "test_id"
        assert info["agent_name"] == "Test Agent"
        assert "capabilities" in info
        assert isinstance(info["capabilities"], list)
    
    def test_match_keywords_exact_match(self):
        """Test keyword matching with exact match"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")
        
        score = agent._match_keywords(
            query="This is a test query",
            keywords=["test"]
        )
        
        assert score > 0
    
    def test_match_keywords_no_match(self):
        """Test keyword matching with no match"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")
        
        score = agent._match_keywords(
            query="completely different words",
            keywords=["test", "sample"]
        )
        
        assert score == 0
    
    def test_match_keywords_multiple_matches(self):
        """Test keyword matching with multiple matches"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")
        
        score = agent._match_keywords(
            query="test sample query",
            keywords=["test", "sample"]
        )
        
        # Should score higher with more matches
        assert score > 0
    
    def test_match_keywords_case_insensitive(self):
        """Test keyword matching is case insensitive"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")
        
        score = agent._match_keywords(
            query="TEST SAMPLE QUERY",
            keywords=["test", "sample"]
        )
        
        assert score > 0
    
    def test_match_keywords_empty_keywords(self):
        """Test keyword matching with empty keywords list"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")
        
        score = agent._match_keywords(
            query="any query",
            keywords=[]
        )
        
        assert score == 0
    
    
    
    def test_can_handle_returns_float(self, mock_business_agent_config):
        """Test can_handle returns float score"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")
        agent.configure(mock_business_agent_config)
        score = agent.can_handle("test query")
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
    
    def test_agent_cannot_be_instantiated_directly(self):
        """Test that BaseBusinessAgent cannot be instantiated"""
        with pytest.raises(TypeError):
            BaseBusinessAgent("id", "name")

    # --------------------------------------
    # ADDITIONAL TESTS START HERE
    # --------------------------------------

    """Tests for new response-building methods in BaseBusinessAgent"""

    @pytest.fixture
    def agent(self):
        return ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")

    def test_build_success_response(self, agent):
        """Ensure success response is built correctly"""
        raw = {
            "status": "success",
            "agent_name": "WeatherAgent",
            "query": "what is tomorrow's forecast for Chicago?",
            "message": "I've got the forecast ready for Chicago tomorrow! Looks like it's going to be a *partly cloudy* kind of day – I'd say the conditions are looking *un-*beleafable! Let me fetch the detailed forecast for you.",
            "confidence": 0.85,
            "data": {},
            "actions": [
                {
                "action_type": "call_tool",
                "description": "Fetch weather forecast for Chicago for tomorrow",
                "payload": {
                    "tool_name": "get_weather_for_location",
                    "arguments": {
                    "location": "Chicago, Illinois",
                    "forecast_date": "tomorrow"
                    }
                }
                }
            ],
            "errors": []
            }
        
        json_str = json.dumps(raw)
        
        response = agent.parse_llm_response(
            query = "test query",
            llm_response = json_str
        )

        assert isinstance(response, BusinessAgentResponse)
        assert response.status == ResponseStatus.SUCCESS
        assert response.agent_name == "WeatherAgent"
        assert response.query == "what is tomorrow's forecast for Chicago?"
        assert response.data == {}
        assert response.message == "I've got the forecast ready for Chicago tomorrow! Looks like it's going to be a *partly cloudy* kind of day – I'd say the conditions are looking *un-*beleafable! Let me fetch the detailed forecast for you."
        assert response.confidence == 0.85
        assert response.actions is not None
        assert len(response.errors) == 0



    def test_build_error_reponse(self, agent):
        response = agent.build_error_response(
            status = ResponseStatus.INTERNAL_ERROR,
            query = "mock query",
            message = "test error message",
            errors = [ErrorResponse(error_code="MOCK_ERROR", error_details="Error message")]
        )

        assert response is not None
        assert isinstance(response, BusinessAgentResponse)
        assert response.status == ResponseStatus.INTERNAL_ERROR
        assert response.agent_name == "Test Agent"
        assert response.query == "mock query"
        assert response.data == {}
        assert response.confidence == 0
        assert len(response.actions) == 0
        assert response.errors == [ErrorResponse(error_code="MOCK_ERROR", error_details="Error message")]


    ''''
    @patch("agents.base_business_agent.LLMFactory.get_llm")
    def test_llm_call_success(self, mock_llm_factory, agent):
        """Test successful LLM call through helper"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content='{"result": "ok"}')
        mock_llm_factory.return_value = mock_llm

        # Configure agent so llm is created
        agent.configure(MagicMock(llm_config=MagicMock()))

        resp = agent.llm_call(messages=[{"role": "user"}], query="hello")

        assert resp.status == ResponseStatus.SUCCESS
        assert resp.data == {"result": "ok"}

    @patch("agents.base_business_agent.LLMFactory.get_llm")
    def test_llm_call_failure(self, mock_llm_factory, agent):
        """LLM call should return structured error response on exception"""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("boom")
        mock_llm_factory.return_value = mock_llm

        agent.configure(MagicMock(llm_config=MagicMock()))

        resp = agent.llm_call(messages=[], query="test")

        assert resp.status == ResponseStatus.ERROR
        assert resp.errors[0].error_code == "LLM_CALL_FAILED"
        assert "boom" in resp.errors[0].error_details
    '''
