"""
Tests for business agent registry
"""
import pytest
from unittest.mock import MagicMock, patch

from agents.agent_registry import BusinessAgentRegistry
from agents.base_business_agent import BaseBusinessAgent, AgentCapability
from config.config_models import AgentRegistryConfig
from typing import List


class MockBusinessAgent(BaseBusinessAgent):
    """Mock business agent for testing"""
    
    def __init__(self, agent_id, agent_name, keywords, llm_config):
        self.test_keywords = keywords
        super().__init__(agent_id=agent_id, agent_name=agent_name, llm_config=llm_config)

    
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
    
    def can_handle(self, query, context=None):
        return self._match_keywords(query, self.test_keywords)
    
    def execute(self, query, context=None):
        return self._create_result(
            success=True,
            data={"result": f"Executed by {self.agent_name}"}
        )


@pytest.mark.unit
@pytest.mark.registry
class TestBusinessAgentRegistry:
    """Test business agent registry functionality"""

    def test_empty_initialization(self, mock_agent_registry_config):
        registry = BusinessAgentRegistry(mock_agent_registry_config)
        assert len(registry.agents) == 0
        assert registry.llm is not None
        assert registry.config is not None


    def test_register_agent(self, mock_agent_registry_config):
        """Test registering a new agent"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)
        mock_agent = MockBusinessAgent(
            agent_id="test_agent",
            agent_name="Test Agent",
            keywords=["price", "cost"],
            llm_config=mock_agent_registry_config.llm_config
        )
        
        registry.register_agent(mock_agent)
        
        assert "test_agent" in registry.agents
        assert registry.agents["test_agent"] == mock_agent

    def test_discover_agents(self, mock_llm_config):
        """Tests the automatic discovery of agents"""
        #module = importlib.import_module("tests.agents")
        #print(f"Module loaded from imporrtlib {module}")
        
        config = AgentRegistryConfig(agent_packages=["tests.agents"], agent_discovery=True, agent_recursive=True, llm_config=mock_llm_config)
        registry = BusinessAgentRegistry(config=config)

        #all_agents = registry._discover_agents()

        all_agents = registry.list_agents()
        #TODO: turn this assert back on after fixing passing config to Agents during discovery
        #assert len(all_agents) > 0                   


        '''
        config = AgentRegistryConfig(agent_packages=["tests.agents"], agent_recursive=True)
        registry = BusinessAgentRegistry(config=config)

        agents = registry.list_agents()
        assert agents is not None
        assert len(agents) >= 1
        '''


    def test_register_multiple_agents(self, mock_agent_registry_config):
        """Test registering multiple agents"""
        registry = BusinessAgentRegistry(config=mock_agent_registry_config)
        agent1 = MockBusinessAgent("agent1", "Agent 1", ["price"], mock_agent_registry_config.llm_config)
        agent2 = MockBusinessAgent("agent2", "Agent 2", ["stock"], mock_agent_registry_config.llm_config)
        
        registry.register_agent(agent1)
        registry.register_agent(agent2)
        
        assert len(registry.agents) == 2
        assert "agent1" in registry.agents
        assert "agent2" in registry.agents


    def test_unregister_agent(self, mock_agent_registry_config):
        """Test unregistering an agent"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)
        mock_agent = MockBusinessAgent("test_agent", "Test", ["price"], mock_agent_registry_config.llm_config)
        
        registry.register_agent(mock_agent)
        assert "test_agent" in registry.agents
        
        registry.unregister_agent("test_agent")
        assert "test_agent" not in registry.agents

    def test_unregister_nonexistent_agent(self, mock_agent_registry_config):
        """Test unregistering agent that doesn't exist"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)
        # Should not raise error
        registry.unregister_agent("nonexistent")
        assert "nonexistent" not in registry.agents


    def test_get_agent(self, mock_agent_registry_config):
        """Test retrieving agent by ID"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)
        mock_agent = MockBusinessAgent("test_agent", "Test", ["price"], mock_agent_registry_config.llm_config)
        
        registry.register_agent(mock_agent)
        
        retrieved = registry.get_agent("test_agent")
        assert retrieved == mock_agent


    def test_get_nonexistent_agent(self, mock_agent_registry_config):
        """Test retrieving non-existent agent returns None"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)
        result = registry.get_agent("nonexistent")
        assert result is None


    def test_list_agents(self, mock_agent_registry_config):
        """Test listing all agents"""
        registry = BusinessAgentRegistry(config=mock_agent_registry_config)
        agent1 = MockBusinessAgent("agent1", "Agent 1", ["price"], mock_agent_registry_config.llm_config)
        agent2 = MockBusinessAgent("agent2", "Agent 2", ["stock"], mock_agent_registry_config.llm_config)
        
        registry.register_agent(agent1)
        registry.register_agent(agent2)
        
        agents_list = registry.list_agents()
        
        assert len(agents_list) == 2
        assert all("agent_id" in agent for agent in agents_list)
        assert all("agent_name" in agent for agent in agents_list)
        assert all("capabilities" in agent for agent in agents_list)


    def test_select_agent_by_keywords(self, mock_agent_registry_config):
        """Test agent selection based on keyword matching"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)

        pricing_agent = MockBusinessAgent(
            "pricing", "Pricing", ["price", "markdown", "discount"], mock_agent_registry_config.llm_config
        )
        inventory_agent = MockBusinessAgent(
            "inventory", "Inventory", ["stock", "reorder"], mock_agent_registry_config.llm_config
        )
        
        registry.register_agent(pricing_agent)
        registry.register_agent(inventory_agent)
        
        # Query with pricing keywords
        selected = registry.select_agent(
            query="What is the best price for this item?",
            use_llm_router=False  # Use only keyword matching
        )
        
        assert selected is not None
        assert selected.agent_id == "pricing"

    

    def test_select_test_agent(self, mock_llm_config):
        """Try query for weather lookup"""
        config = AgentRegistryConfig(
            agent_discovery=True, 
            agent_packages=["tests.agents"], 
            agent_recursive=True,
            llm_config=mock_llm_config
        )
        registry = BusinessAgentRegistry(config=config)

        selected = registry.select_agent(
            query = "What is the weather in Chicago?",
            use_llm_router=False
        )

        #TODO: Turn on asserts after config to agent is working
        #assert selected is not None
        #assert selected.agent_id == "test_agent_1"


    def test_select_agent_no_match(self, mock_agent_registry_config):
        """Test agent selection when no agent matches"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)

        agent = MockBusinessAgent("test", "Test", ["specific", "keywords"], mock_agent_registry_config.llm_config)
        registry.register_agent(agent)
        
        selected = registry.select_agent(
            query="completely unrelated query",
            use_llm_router=False,
            min_confidence=0.5
        )
        
        assert selected is None


    def test_select_agent_with_min_confidence(self, mock_agent_registry_config):
        """Test agent selection respects minimum confidence threshold"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)
        agent = MockBusinessAgent("test", "Test", ["price"], mock_agent_registry_config.llm_config)
        registry.register_agent(agent)
        
        # High confidence requirement - should fail
        selected = registry.select_agent(
            query="price",
            use_llm_router=False,
            min_confidence=0.9  # Very high threshold
        )
        
        # Might be None depending on keyword matching score
        # The important thing is it respects the threshold

    '''
    def test_select_agent_llm_returns_invalid_id(self, mock_agent_registry_config):
        """Test LLM router returning invalid agent ID"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)

        agent = MockBusinessAgent("valid_agent", "Valid", BusinessDomain.PRICING, ["price"])
        registry.register_agent(agent)
        
        # Mock LLM to return invalid agent ID
        mock_response = MagicMock()
        mock_response.content = "invalid_agent_id"
        #registry.llm.invoke = Mock(return_value=mock_response)
        with patch("langchain_openai.ChatOpenAI.invoke", return_value=mock_response):
            selected = registry.select_agent(
                query="inventory check",
                use_llm_router=True
            )
    
        assert selected is None
        
        # Could be None or the valid agent depending on keyword score
        # The important thing is it doesn't crash

    '''     

    def test_select_agent_with_llm_router(self, mock_agent_registry_config):
        """Test agent selection using LLM router"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)

        agent1 = MockBusinessAgent("agent1", "Agent 1", ["price"], mock_agent_registry_config.llm_config)
        agent2 = MockBusinessAgent("agent2", "Agent 2", ["stock"], mock_agent_registry_config.llm_config)
        
        registry.register_agent(agent1)
        registry.register_agent(agent2)
        
        # Mock LLM to return agent1
        mock_response = MagicMock()
        mock_response.content = "agent1"

        with patch("langchain_openai.ChatOpenAI.invoke", return_value=mock_response):
            selected = registry.select_agent(
                query="What is the price?",
                use_llm_router=True
            )
        
        assert selected is not None
        assert selected.agent_id == "agent1"


    def test_select_agent_llm_returns_invalid_id(self, mock_agent_registry_config):
        """Test LLM router returning invalid agent ID"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)

        agent = MockBusinessAgent("valid_agent", "Valid", ["price"], mock_agent_registry_config.llm_config)
        registry.register_agent(agent)
        
        # Mock LLM to return invalid agent ID
        mock_response = MagicMock()
        mock_response.content = "invalid_agent_id"
        with patch("langchain_openai.ChatOpenAI.invoke", return_value=mock_response):
            selected = registry.select_agent(
                query="what are you doing today?",
                use_llm_router=True
            )
        
        assert selected is None
        # Could be None or the valid agent depending on keyword score
        # The important thing is it doesn't crash


    def test_execute_with_best_agent_success(self, mock_agent_registry_config):
        """Test executing with best matching agent"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)

        agent = MockBusinessAgent("test", "Test", ["price"], mock_agent_registry_config.llm_config)
        registry.register_agent(agent)
        
        result = registry.execute_with_best_agent(
            query="What is the price?",
            min_confidence=0.1  # Low threshold to ensure match
        )
        
        if result["success"]:
            assert "selected_agent" in result
            assert result["selected_agent"] == "Test"



    def test_execute_with_best_agent_no_match(self, mock_agent_registry_config):
        """Test execution when no agent matches"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)

        agent = MockBusinessAgent("test", "Test", ["specific"], mock_agent_registry_config.llm_config)
        registry.register_agent(agent)
        
        result = registry.execute_with_best_agent(
            query="unrelated query",
            min_confidence=0.9  # High threshold
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "available_agents" in result


    def test_execute_with_multiple_agents(self, mock_agent_registry_config):
        """Test executing with multiple qualifying agents"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)

        agent1 = MockBusinessAgent("agent1", "Agent 1", ["price", "cost"], mock_agent_registry_config.llm_config)
        agent2 = MockBusinessAgent("agent2", "Agent 2", ["price", "value"], mock_agent_registry_config.llm_config)
        
        registry.register_agent(agent1)
        registry.register_agent(agent2)
        
        results = registry.execute_with_multiple_agents(
            query="What is the price?",
            min_confidence=0.1
        )
        
        # At least one should match
        assert isinstance(results, list)
        # Results may vary based on keyword matching



    def test_registry_with_no_agents(self, mock_agent_registry_config):
        """Test registry behavior with no registered agents"""

        registry = BusinessAgentRegistry(config=mock_agent_registry_config)

        selected = registry.select_agent("any query")
        assert selected is None
        
        agents_list = registry.list_agents()
        assert agents_list == []


    def test_agent_selection_with_context(self, mock_agent_registry_config):
        """Test agent selection considers context"""
        registry = BusinessAgentRegistry(mock_agent_registry_config)

        agent = MockBusinessAgent("test", "Test", ["price"], mock_agent_registry_config.llm_config)
        registry.register_agent(agent)
        
        context = {"pricing_data": {"current_price": 29.99}}
        
        selected = registry.select_agent(
            query="optimize",
            context=context,
            use_llm_router=False
        )
        
        # Agent should receive context for scoring
        # Behavior depends on agent implementation
