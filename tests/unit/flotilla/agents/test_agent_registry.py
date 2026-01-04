"""
Tests for business agent registry
"""
import pytest
from unittest.mock import MagicMock, patch

from flotilla.agents.agent_registry import BusinessAgentRegistry
from flotilla.agents.base_business_agent import BaseBusinessAgent, AgentCapability, ToolDependency
from flotilla.agents.business_agent_response import BusinessAgentResponse, ErrorResponse, ResponseStatus
from flotilla.tools.tool_registry import ToolRegistry
from flotilla.selectors.keyword_agent_selector import KeywordAgentSelector
from typing import List


class MockBusinessAgent(BaseBusinessAgent):
    """Mock business agent for testing"""
    
    def __init__(self, agent_id, agent_name, llm, checkpointer, keywords):
        self.test_keywords = keywords
        super().__init__(agent_id=agent_id, agent_name=agent_name, llm=llm, checkpointer=checkpointer)

    
    def _initialize_capabilities(self) -> List[AgentCapability]:
        capabilities = [
            AgentCapability(
                name="test_capability",
                description="Test capability",
                keywords=self.test_keywords,
                examples=["test query"]
            )
        ]
        return capabilities
    
    def _initialize_dependencies(self) -> List[ToolDependency]:
        return []
        




@pytest.mark.unit
class TestBusinessAgentRegistry:
    """Test business agent registry functionality"""

    def test_empty_initialization(self):
        tool_registry = ToolRegistry(tool_providers=[])
        registry = BusinessAgentRegistry(agents = {}, agent_selector=None, tool_registry=tool_registry)
        assert len(registry._agents) == 0
        assert registry._tool_registry is not None


    def test_register_multiple_agents(self, mock_checkpointer, mock_agent_selector, mock_tool_registry, mock_llm):
        """Test registering multiple agents"""
        agent1 = MockBusinessAgent(agent_id="agent1", agent_name="Agent 1", llm=mock_llm, checkpointer=mock_checkpointer, keywords=["price"])
        agent2 = MockBusinessAgent(agent_id="agent2", agent_name="Agent 2", llm=mock_llm, checkpointer=mock_checkpointer, keywords=["stock"])
        agents = {
            "agent1": agent1,
            "agent2": agent2
        }
        registry = BusinessAgentRegistry(agents=agents, tool_registry=mock_tool_registry, agent_selector=mock_agent_selector)
        
        assert len(registry._agents) == 2
        assert "agent1" in registry._agents.keys()
        assert "agent2" in registry._agents.keys()



    def test_get_agent(self,mock_tool_registry,mock_agent_selector, mock_llm, mock_checkpointer):
        """Test retrieving agent by ID"""
        agent1 = MockBusinessAgent(agent_id="agent1", agent_name="Agent 1", llm=mock_llm, checkpointer=mock_checkpointer, keywords=["price"])
        agent2 = MockBusinessAgent(agent_id="agent2", agent_name="Agent 2", llm=mock_llm, checkpointer=mock_checkpointer, keywords=["stock"])
        agents = {
            "agent1": agent1,
            "agent2": agent2
        }
        registry = BusinessAgentRegistry(agents=agents, tool_registry=mock_tool_registry, agent_selector=mock_agent_selector)
        
        retrieved = registry.get_agent("agent1")
        assert retrieved == agent1


    def test_get_nonexistent_agent(self, mock_tool_registry,mock_agent_selector, mock_llm, mock_checkpointer):
        """Test retrieving non-existent agent returns None"""
        agent1 = MockBusinessAgent(agent_id="agent1", agent_name="Agent 1", llm=mock_llm, checkpointer=mock_checkpointer, keywords=["price"])
        agent2 = MockBusinessAgent(agent_id="agent2", agent_name="Agent 2", llm=mock_llm, checkpointer=mock_checkpointer, keywords=["stock"])
        agents = {
            "agent1": agent1,
            "agent2": agent2
        }
        registry = BusinessAgentRegistry(agents=agents, tool_registry=mock_tool_registry, agent_selector=mock_agent_selector)
        
        retrieved = registry.get_agent("agent3")
        assert retrieved is None


    def test_list_agents(self, mock_tool_registry,mock_agent_selector, mock_llm, mock_checkpointer ):
        """Test listing all agents"""
        agent1 = MockBusinessAgent(agent_id="agent1", agent_name="Agent 1", llm=mock_llm, checkpointer=mock_checkpointer, keywords=["price"])
        agent2 = MockBusinessAgent(agent_id="agent2", agent_name="Agent 2", llm=mock_llm, checkpointer=mock_checkpointer, keywords=["stock"])
        agents = {
            "agent1": agent1,
            "agent2": agent2
        }
        registry = BusinessAgentRegistry(agents=agents, tool_registry=mock_tool_registry, agent_selector=mock_agent_selector)
        
        agents_list = registry.list_agents()
        
        assert len(agents_list) == 2
        assert all("agent_id" in agent for agent in agents_list)
        assert all("agent_name" in agent for agent in agents_list)
        assert all("capabilities" in agent for agent in agents_list)


    def test_select_agent_by_keywords(self, mock_tool_registry, mock_agent_selector, mock_llm, mock_checkpointer):
        """Test agent selection based on keyword matching"""
        agent1 = MockBusinessAgent(agent_id="agent1", agent_name="Agent 1", llm=mock_llm, checkpointer=mock_checkpointer, keywords=["price"])
        agent2 = MockBusinessAgent(agent_id="agent2", agent_name="Agent 2", llm=mock_llm, checkpointer=mock_checkpointer, keywords=["stock"])
        agents = {
            "agent1": agent1,
            "agent2": agent2
        }
        registry = BusinessAgentRegistry(agents=agents, tool_registry=mock_tool_registry, agent_selector=mock_agent_selector)
        #registry.startup()

        # Query with pricing keywords
        selected = registry.select_agent(
            query="What is the best price for this item?"
        )
        
        assert selected is not None
        assert selected.agent_id == "agent1"

    


    def test_select_agent_no_match(self, mock_tool_registry, mock_llm, mock_agent_selector, mock_checkpointer):
        """Test agent selection when no agent matches"""
        agent1 = MockBusinessAgent(agent_id="agent1", agent_name="Agent 1", llm=mock_llm, checkpointer=mock_checkpointer, keywords=["price"])
        agent2 = MockBusinessAgent(agent_id="agent2", agent_name="Agent 2", llm=mock_llm, checkpointer=mock_checkpointer, keywords=["stock"])
        agents = {
            "agent1": agent1,
            "agent2": agent2
        }
        registry = BusinessAgentRegistry(agents=agents, tool_registry=mock_tool_registry, agent_selector=mock_agent_selector)
        #registry.startup()

        # Query with pricing keywords
        selected = registry.select_agent(
            query="What is the name for this item?"
        )
        
        assert selected is None

    def test_startup_calls_agent_startup_and_attach_tools(
        self,
        mock_tool_registry,
        mock_agent_selector,
        mock_llm,
        mock_checkpointer
    ):
        """Test that startup attaches tools and calls agent.startup()"""
        agent = MockBusinessAgent(
            agent_id="agent1",
            agent_name="Agent 1",
            llm=mock_llm,
            checkpointer=mock_checkpointer,
            keywords=["price"]
        )

        # Spy on lifecycle methods
        agent.startup = MagicMock()
        agent.attach_tools = MagicMock()

        registry = BusinessAgentRegistry(
            agents={"agent1": agent},
            tool_registry=mock_tool_registry,
            agent_selector=mock_agent_selector
        )

        registry.start()

        agent.attach_tools.assert_called_once()
        agent.startup.assert_called_once()


    def test_startup_with_no_agents_does_not_error(
        self,
        mock_tool_registry,
        mock_agent_selector
    ):
        """Test startup safely handles empty registry"""
        registry = BusinessAgentRegistry(
            agents={},
            tool_registry=mock_tool_registry,
            agent_selector=mock_agent_selector
        )

        # Should not raise
        registry.start()


    def test_execute_with_best_agent_success(
        self,
        mock_tool_registry,
        mock_agent_selector,
        mock_llm,
        mock_checkpointer
    ):
        """Test execute_with_best_agent executes selected agent"""
        agent = MockBusinessAgent(
            agent_id="agent1",
            agent_name="Agent 1",
            llm=mock_llm,
            checkpointer=mock_checkpointer,
            keywords=["price"]
        )

        expected_response = BusinessAgentResponse(
            status=ResponseStatus.SUCCESS,
            agent_name=agent.agent_name,
            confidence=0.8,
            query="What is the price?",
            result={"answer": "10"}
        )

        agent.execute = MagicMock(return_value=expected_response)

        registry = BusinessAgentRegistry(
            agents={"agent1": agent},
            tool_registry=mock_tool_registry,
            agent_selector=mock_agent_selector
        )

        response = registry.execute_with_best_agent(
            query="What is the price?"
        )

        agent.execute.assert_called_once_with("What is the price?", None)
        assert response == expected_response
        assert response.status == ResponseStatus.SUCCESS


    def test_execute_with_best_agent_no_match_returns_error(
        self,
        mock_tool_registry,
        mock_agent_selector
    ):

        registry = BusinessAgentRegistry(
            agents={},
            tool_registry=mock_tool_registry,
            agent_selector=mock_agent_selector
        )

        response = registry.execute_with_best_agent(
            query="Unknown query"
        )

        assert isinstance(response, BusinessAgentResponse)
        assert response.status == ResponseStatus.NO_VALID_AGENT
        assert response.query == "Unknown query"


    def test_shutdown_calls_agent_shutdown(
        self,
        mock_tool_registry,
        mock_agent_selector,
        mock_llm,
        mock_checkpointer
    ):
        """Test shutdown calls shutdown on all registered agents"""
        agent1 = MockBusinessAgent(
            agent_id="agent1",
            agent_name="Agent 1",
            llm=mock_llm,
            checkpointer=mock_checkpointer,
            keywords=["price"]
        )
        agent2 = MockBusinessAgent(
            agent_id="agent2",
            agent_name="Agent 2",
            llm=mock_llm,
            checkpointer=mock_checkpointer,
            keywords=["stock"]
        )

        agent1.shutdown = MagicMock()
        agent2.shutdown = MagicMock()

        registry = BusinessAgentRegistry(
            agents={
                "agent1": agent1,
                "agent2": agent2
            },
            tool_registry=mock_tool_registry,
            agent_selector=mock_agent_selector
        )

        registry.shutdown()

        agent1.shutdown.assert_called_once()
        agent2.shutdown.assert_called_once()

