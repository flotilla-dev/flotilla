"""
Tests for orchestration agent
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from datetime import datetime

from agents.orchestration_agent import OrchestrationAgent
from config.config_models import OrchestrationConfig


@pytest.mark.unit
@pytest.mark.orchestration
class TestOrchestrationAgent:
    """Test orchestration agent functionality"""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Mock LLM provider"""
        with patch('agents.orchestration_agent.LLMFactory') as mock_provider_class:
            mock_provider = MagicMock()
            mock_llm = MagicMock()
            mock_provider.get_llm.return_value = mock_llm
            mock_provider_class.return_value = mock_provider
            yield mock_provider_class, mock_llm
    
    @pytest.fixture
    def orchestration_agent(self, mock_orchestration_config, mock_llm_provider):
        """Create orchestration agent with mocked dependencies"""
        mock_provider_class, mock_llm = mock_llm_provider
        agent = OrchestrationAgent(mock_orchestration_config)
        return agent
        
    
    def test_initialization(self, mock_orchestration_config, mock_llm_provider):
        """Test agent initializes correctly"""
        mock_provider_class, mock_llm = mock_llm_provider
        
        with patch('agents.orchestration_agent.create_agent'):
            agent = OrchestrationAgent(config=mock_orchestration_config)
            
            assert agent.config == mock_orchestration_config
            assert agent.llm is not None
            #assert agent.checkpointer is not None
            assert agent.tools is not None
            assert agent.business_registry is not None
    
    '''
    def test_create_checkpointer(self, orchestration_agent):
        """Test checkpointer creation"""
        checkpointer = orchestration_agent._create_checkpointer()
        
        assert checkpointer is not None
        # Verify it's an InMemorySaver instance
        from langgraph.checkpoint.memory import InMemorySaver
        assert isinstance(checkpointer, InMemorySaver)
    '''
    
    
    def test_execute_success(self, orchestration_agent):
        """Test successful query execution"""
        # Mock agent_executor for execute method
        orchestration_agent.business_registry = MagicMock()
        orchestration_agent.business_registry.execute_with_best_agent.return_value = {
            "result": "Test response",
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "selected_agent": "mock_agent"
        }
        
        result = orchestration_agent.execute("test query")
        
        assert result["success"] is True
        assert result["result"] == "Test response"
        assert "timestamp" in result
    
    def test_execute_failure(self, orchestration_agent):
        """Test query execution handles errors"""
        # Mock agent_executor to raise exception
        orchestration_agent.business_registry = MagicMock()
        orchestration_agent.business_registry.execute_with_best_agent.side_effect = Exception("Test error")

        
        result = orchestration_agent.execute("test query")
        
        assert result["success"] is False
        assert result["query"] == "test query"
        assert "error" in result
        assert "Test error" in result["error"]
        assert "timestamp" in result
    
    