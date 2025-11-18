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
        resp = agent.build_success_response(
            query="weather in chicago",
            data={"temp": "72F"},
            message="OK",
            confidence=0.8,
            actions=[{"type": "next"}],
        )

        assert isinstance(resp, BusinessAgentResponse)
        assert resp.status == ResponseStatus.SUCCESS
        assert resp.agent_name == "Test Agent"
        assert resp.query == "weather in chicago"
        assert resp.data == {"temp": "72F"}
        assert resp.message == "OK"
        assert resp.confidence == 0.8
        assert resp.actions == [{"type": "next"}]
        assert resp.errors is None

    def test_build_error_response(self, agent):
        """Ensure error response is built correctly"""
        resp = agent.build_error_response(
            query="invalid",
            error_code="SOME_ERROR",
            error_details="details here",
            message="Failed",
        )

        assert resp.status == ResponseStatus.ERROR
        assert resp.agent_name == "Test Agent"
        assert resp.query == "invalid"
        assert resp.message == "Failed"
        assert resp.confidence == 0.0
        assert resp.data == {}
        assert isinstance(resp.errors, list)
        assert resp.errors[0].error_code == "SOME_ERROR"
        assert resp.errors[0].error_details == "details here"

    def test_parse_json_response_valid_json(self, agent):
        """Test JSON parsing helper with valid JSON string"""
        raw = '{"a": 1, "b": 2}'
        parsed = agent._parse_json_response(raw)
        assert parsed == {"a": 1, "b": 2}

    def test_parse_json_response_invalid_json(self, agent):
        """Should fall back to raw response wrapper"""
        raw = "not-json"
        parsed = agent._parse_json_response(raw)
        assert parsed == {"raw_response": "not-json"}

    def test_parse_json_response_dict(self, agent):
        """If dict is passed, return unchanged"""
        parsed = agent._parse_json_response({"x": 7})
        assert parsed == {"x": 7}

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

    def test_run_internal_agent_success(self, agent):
        """run_internal_agent should return success response"""
        agent.agent = MagicMock()
        agent.agent.invoke.return_value = {"val": 123}

        resp = agent.run_internal_agent(query="hi")

        assert resp.status == ResponseStatus.SUCCESS
        assert resp.data == {"result": {"val": 123}}

    def test_run_internal_agent_not_initialized(self, agent):
        """If .agent was never set, return structured error"""
        resp = agent.run_internal_agent(query="hi")

        assert resp.status == ResponseStatus.ERROR
        assert resp.errors[0].error_code == "AGENT_NOT_INITIALIZED"

    def test_run_internal_agent_failure(self, agent):
        """Exception inside internal agent should produce structured error"""
        agent.agent = MagicMock()
        agent.agent.invoke.side_effect = Exception("oops")

        resp = agent.run_internal_agent(query="boom")

        assert resp.status == ResponseStatus.ERROR
        assert resp.errors[0].error_code == "AGENT_EXECUTION_FAILED"
        assert "oops" in resp.errors[0].error_details
