"""
Tests for base business agent
"""
import pytest
from datetime import datetime

from flotilla.agents.base_business_agent import (
    BaseBusinessAgent,
    AgentCapability,
    ToolDependency
)

from unittest.mock import Mock, MagicMock, patch


from flotilla.agents.business_agent_response import (
    BusinessAgentResponse, 
    ErrorResponse,
    ResponseStatus
)

from flotilla.config_models import LLMConfig

from typing import List

import json


class ConcreteBusinessAgent(BaseBusinessAgent):
    """Concrete implementation for testing"""
    
    def __init__(self, agent_id:str, agent_name:str, llm, checkpointer):
        self.test_keywords = ["test", "sample"]
        super().__init__(agent_id=agent_id, agent_name=agent_name, llm=llm, checkpointer=checkpointer)
        
    
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
    
    def _initialize_dependencies(self) -> List[ToolDependency]:
        dependencies = [ToolDependency(tool_name="mock_tool",required= True)]
        return dependencies

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

class TestToolDependency:

    def test_create_tool_dependency(self):
        dependency = ToolDependency(
            tool_name="test_tool",
            required=False
        )

        assert dependency
        assert dependency.tool_name == "test_tool"
        assert dependency.required is False

    def test_defaults(self):
        dependency  = ToolDependency(
            tool_name="test_tool"
        )

        assert dependency.required is True
        


@pytest.mark.unit
class TestBaseBusinessAgent:
    """Test base business agent functionality"""
    
    def test_initialization(self, mock_llm, mock_checkpointer):
        """Test agent initializes correctly"""
        agent = ConcreteBusinessAgent(
            agent_id="test_id",
            agent_name="Test Name", 
            llm=mock_llm, checkpointer=mock_checkpointer
            )
        
        assert agent.agent_id == "test_id"
        assert agent.agent_name == "Test Name"
        assert agent._checkpointer is mock_checkpointer
        assert agent._llm is mock_llm
    
    def test_get_capabilities(self, mock_llm, mock_checkpointer):
        """Test retrieving agent capabilities"""
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent", llm=mock_llm, checkpointer=mock_checkpointer)

        capabilities = agent.get_capabilities()
        
        assert isinstance(capabilities, list)
        assert len(capabilities) == 1
        assert all(isinstance(cap, AgentCapability) for cap in capabilities)

    def test_get_dependencies(self, mock_llm, mock_checkpointer):
        agent = ConcreteBusinessAgent(agent_id="test_id", agent_name="Test Agent", llm=mock_llm, checkpointer=mock_checkpointer)
        dependencies = agent.get_tool_dependencis()

        assert isinstance(dependencies, list)
        assert len(dependencies) == 1
        assert all(isinstance(dep, ToolDependency) for dep in dependencies)
    
    def test_get_info(self, mock_checkpointer, mock_llm):
        """Test getting agent information"""
        agent = ConcreteBusinessAgent(
            agent_id="test_id",
            agent_name="Test Agent", llm=mock_llm, checkpointer=mock_checkpointer
            )
        
        info = agent.get_info()
        
        assert info["agent_id"] == "test_id"
        assert info["agent_name"] == "Test Agent"
        assert "capabilities" in info
        assert isinstance(info["capabilities"], list)
    
    def test_agent_cannot_be_instantiated_directly(self):
        """Test that BaseBusinessAgent cannot be instantiated"""
        with pytest.raises(TypeError):
            BaseBusinessAgent("id", "name")

    def test_startup_initializes_agent_and_sets_started(self, mock_llm, mock_checkpointer):
        agent = ConcreteBusinessAgent(
            agent_id="test_id",
            agent_name="Test Agent",
            llm=mock_llm,
            checkpointer=mock_checkpointer,
        )

        with patch.object(agent, "_create_internal_agent") as mock_create:
            agent.startup()

            mock_create.assert_called_once()
            assert agent.started is True

    def test_shutdown_sets_started_false(self, mock_llm, mock_checkpointer):
        agent = ConcreteBusinessAgent(
            agent_id="test_id",
            agent_name="Test Agent",
            llm=mock_llm,
            checkpointer=mock_checkpointer,
        )

        agent.started = True
        agent.shutdown()

        assert agent.started is False


    def test_attach_tools_sets_tools(self, mock_llm, mock_checkpointer):
        agent = ConcreteBusinessAgent(
            agent_id="test_id",
            agent_name="Test Agent",
            llm=mock_llm,
            checkpointer=mock_checkpointer,
        )

        tools = [Mock(), Mock()]
        agent.attach_tools(tools)

        assert agent.tools == tools

    def test_execute_returns_error_when_agent_not_initialized(self, mock_llm, mock_checkpointer):
        agent = ConcreteBusinessAgent(
            agent_id="test_id",
            agent_name="Test Agent",
            llm=mock_llm,
            checkpointer=mock_checkpointer,
        )

        response = agent.execute("test query")

        assert isinstance(response, BusinessAgentResponse)
        assert response.status == ResponseStatus.APP_MISCONFIGURED
        assert any(
            err.error_code == "AGENT_NOT_INITIALIZED"
            for err in response.errors
        )

    def test_execute_returns_error_when_llm_raises_exception(self, mock_llm, mock_checkpointer):
        agent = ConcreteBusinessAgent(
            agent_id="test_id",
            agent_name="Test Agent",
            llm=mock_llm,
            checkpointer=mock_checkpointer,
        )

        # Fake internal agent with failing invoke
        agent.agent = Mock()
        agent.agent.invoke.side_effect = RuntimeError("LLM failure")

        response = agent.execute("test query")

        assert response.status == ResponseStatus.LLM_CALL_FAILED
        assert any(
            err.error_code == "AGENT_EXECUTION_FAILED"
            for err in response.errors
        )
