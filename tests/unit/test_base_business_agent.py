"""
Tests for base business agent
"""
import pytest
from datetime import datetime

from agents.base_business_agent import (
    BaseBusinessAgent,
    AgentCapability
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
    
    def test_create_result_success(self):
        """Test creating successful result"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")
        
        result = agent._create_result(
            success=True,
            data={"test": "data"}
        )
        
        assert result["success"] is True
        assert result["data"] == {"test": "data"}
        assert result["agent_id"] == agent.agent_id
        assert result["agent_name"] == agent.agent_name
        assert "timestamp" in result
    
    def test_create_result_failure(self):
        """Test creating failure result"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")
        
        result = agent._create_result(
            success=False,
            error="Test error message"
        )
        
        assert result["success"] is False
        assert result["error"] == "Test error message"
        assert "agent_id" in result
        assert "timestamp" in result
    
    def test_create_result_with_metadata(self):
        """Test creating result with metadata"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")
        
        metadata = {"source": "test", "version": "1.0"}
        
        result = agent._create_result(
            success=True,
            data={"test": "data"},
            metadata=metadata
        )
        
        assert result["metadata"] == metadata
    
    def test_execute_returns_standardized_result(self, mock_business_agent_config):
        """Test execute method returns standardized result"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")
        agent.configure(mock_business_agent_config)
        result = agent.execute("test query")
        
        assert "success" in result
        assert "agent_id" in result
        assert "agent_name" in result
        assert "timestamp" in result
    
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
    
    def test_timestamp_format(self, mock_business_agent_config):
        """Test that timestamp is in ISO format"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent")
        agent.configure(mock_business_agent_config)
        result = agent._create_result(success=True, data={})
        
        # Should be parseable as ISO datetime
        timestamp = result["timestamp"]
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)