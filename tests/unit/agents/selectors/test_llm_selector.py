import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage

from typing import List
from agents.base_business_agent import BaseBusinessAgent, AgentCapability
from agents.selectors.llm_agent_selector import LLMAgentSelector
from config.config_models import LLMAgentSelectorConfig, LLMConfig
from agents.business_agent_response import BusinessAgentResponse, ErrorResponse, ResponseStatus



class MockBusinessAgent(BaseBusinessAgent):
    """Mock business agent for testing"""
    
    def __init__(self, agent_id, agent_name, keywords):
        self.test_keywords = keywords
        super().__init__(agent_id=agent_id, agent_name=agent_name)

    
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
    
    def execute(self, query, context = None) -> BusinessAgentResponse:
        return BusinessAgentResponse(
            status=ResponseStatus.SUCCESS,
            agent_name=self.agent_name,
            query=query,
            confidence=1,
            data={},
            actions=[],
            errors=[]
        )



@pytest.fixture
def selector(mock_llm_config):
    config = LLMAgentSelectorConfig(
        llm_config=mock_llm_config,
        min_confidence=0.6
    )

    return LLMAgentSelector(config)


class TestLLMAgentSelector:

    def test_select_agent_success(self, selector, mock_llm):
        agents = {
            "weather": MockBusinessAgent(
                agent_id="weather",
                agent_name="WeatherAgent",
                keywords=["forecast"],
            ), 
            "sports": MockBusinessAgent(
                agent_id="sports",
                agent_name="SportsAgent",
                keywords=["scores"],
            )
        }

        # force creation of the capabilities
        for agent in agents.values():
            agent._capabilities = agent._initialize_capabilities()

        # LLM returns JSON selecting weather agent
        mock_llm.invoke.return_value = AIMessage(
            content='{"agent_id": "weather", "confidence": 0.92}'
        )
        selector.llm = mock_llm

        result = selector.select_agent("what is the weather tomorrow?", agents)

        assert result is agents["weather"]
        mock_llm.invoke.assert_called_once()


    def test_reject_low_confidence(self, selector, mock_llm):
        agents = {
            "weather": MockBusinessAgent(
                agent_id="weather",
                agent_name="WeatherAgent",
                keywords=["forecast"],
            )}

        # force creation of the capabilities
        for agent in agents.values():
            agent._capabilities = agent._initialize_capabilities()

        # Confidence below threshold
        mock_llm.invoke.return_value = AIMessage(
            content='{"agent_id": "weather", "confidence": 0.2}'
        )
        selector.llm = mock_llm


        result = selector.select_agent("weather?", agents)

        assert result is None


    def test_unknown_agent_id(self, selector, mock_llm, caplog):
        agents = {
            "weather": MockBusinessAgent(
                agent_id="weather",
                agent_name="WeatherAgent",
                keywords=["forecast"],
            ), 
            "sports": MockBusinessAgent(
                agent_id="sports",
                agent_name="SportsAgent",
                keywords=["scores"],
            )
        }

        # force creation of the capabilities
        for agent in agents.values():
            agent._capabilities = agent._initialize_capabilities()

        # Agent ID that does not exist in agents dict
        mock_llm.invoke.return_value = AIMessage(
            content='{"agent_id": "not-real", "confidence": 0.9}'
        )
        selector.llm = mock_llm


        result = selector.select_agent("location?", agents)

        assert result is None
        assert any("unknown agent id" in m.lower() for m in caplog.messages)
