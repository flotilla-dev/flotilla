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
