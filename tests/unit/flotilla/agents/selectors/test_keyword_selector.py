"""
PyTest suite for KeywordAgentSelector
"""
import pytest
from unittest.mock import Mock
from flotilla.agents.selectors.keyword_agent_selector import KeywordAgentSelector
from flotilla.agents.base_business_agent import BaseBusinessAgent, AgentCapability


# ==========================================
# Fixtures
# ==========================================


@pytest.fixture
def weather_agent(agent_factory):
    return agent_factory(
        agent_id = "weather_agent",
        capabilities = [
            AgentCapability(
                name="Weather Forecast",
                description="Provides weather forecasts and current conditions",
                keywords=["weather", "temperature", "forecast", "rain", "climate"],
                examples=["What's the weather today?", "Will it rain tomorrow?"]
            )
        ], 
        dependencies = []
    )
   


@pytest.fixture
def calculator_agent(agent_factory):
    return agent_factory(
        agent_id = "calculator_agent",
        capabilities = [
            AgentCapability(
                name="Math Calculations",
                description="Performs mathematical calculations and equations",
                keywords=["math", "calculate", "equation", "arithmetic", "compute"],
                examples=["Calculate 25 * 48", "What is 15% of 200?"]
            )
        ],
        dependencies = []
    )


@pytest.fixture
def calendar_agent(agent_factory):
    return agent_factory(
        agent_id = "calendar_agent",
        capabilities = [
            AgentCapability(
                name="Schedule Management",
                description="Manages appointments, schedules, and events",
                keywords=["schedule", "calendar", "appointment", "meeting", "event"],
                examples=["Schedule a meeting", "What's on my calendar?"]
            )
        ],
        dependencies = []
    )




@pytest.fixture
def multi_capability_agent(agent_factory):
    return agent_factory(
        agent_id = "multi_agent",
        capabilities = [
            AgentCapability(
                name="Weather",
                description="Weather info",
                keywords=["weather", "temperature"],
                examples=[]
            ),
            AgentCapability(
                name="Time",
                description="Time info",
                keywords=["time", "clock", "hour"],
                examples=[]
            )
        ],
        dependencies = []
    )

@pytest.fixture
def keyword_selector():
    return KeywordAgentSelector(min_confidence=0.2)


@pytest.mark.unit
class TestKeywordSelector:

    def test_constructor(self):
        """Test that constructor sets correct selector name"""
        selector = KeywordAgentSelector(min_confidence=0.6)

        assert selector.selector_name == "KeywordAgentSelector"
        assert selector.min_confidence == 0.6

    def test_select_agent_finds_weather_agent(
        self,
        weather_agent,
        calculator_agent,
        calendar_agent
    ):
        """Test that weather query selects weather agent"""
        selector = KeywordAgentSelector(min_confidence=0.2)
        query = "What's the weather like today?"

        agents = {
            weather_agent.agent_id: weather_agent,
            calculator_agent.agent_id: calculator_agent,
            calendar_agent.agent_id: calendar_agent,
        }

        selected = selector.select_agent(
            query=query,
            agents=agents
        )

        assert selected == weather_agent

    def test_select_agent_finds_calculator_agent(
        self,
        keyword_selector,
        weather_agent,
        calculator_agent,
        calendar_agent
    ):
        """Test that math query selects calculator agent"""
        agents = {
            weather_agent.agent_id: weather_agent,
            calculator_agent.agent_id: calculator_agent,
            calendar_agent.agent_id: calendar_agent,
        }

        query = "Calculate 15 times 23"
        selected = keyword_selector.select_agent(query, agents)

        assert selected == calculator_agent

    def test_select_agent_finds_calendar_agent(
        self,
        keyword_selector,
        weather_agent,
        calculator_agent,
        calendar_agent
    ):
        """Test that schedule query selects calendar agent"""
        agents = {
            weather_agent.agent_id: weather_agent,
            calculator_agent.agent_id: calculator_agent,
            calendar_agent.agent_id: calendar_agent,
        }

        query = "Schedule a meeting for tomorrow"
        selected = keyword_selector.select_agent(query, agents)

        assert selected == calendar_agent

    def test_select_agent_multiple_keyword_matches(
        self,
        keyword_selector,
        weather_agent
    ):
        """Test query with multiple matching keywords"""
        agents = {
            weather_agent.agent_id: weather_agent
        }

        query = "What's the weather and temperature forecast today?"
        selected = keyword_selector.select_agent(query, agents)

        assert selected == weather_agent

    def test_select_agent_case_insensitive(
        self,
        keyword_selector,
        weather_agent
    ):
        """Test that keyword matching is case insensitive"""
        agents = {
            weather_agent.agent_id: weather_agent
        }

        query = "WEATHER FORECAST"
        selected = keyword_selector.select_agent(query, agents)

        assert selected == weather_agent

    def test_select_agent_partial_keyword_match(
        self,
        keyword_selector,
        calculator_agent
    ):
        """Test that partial keyword matches work"""
        agents = {
            calculator_agent.agent_id: calculator_agent
        }

        query = "I need to calculate something"
        selected = keyword_selector.select_agent(query, agents)

        assert selected == calculator_agent

    def test_select_agent_returns_none_below_threshold(
        self,
        keyword_selector,
        weather_agent,
        calculator_agent
    ):
        """Test that no agent is selected if all scores below threshold"""
        keyword_selector.min_confidence = 0.99

        agents = {
            weather_agent.agent_id: weather_agent,
            calculator_agent.agent_id: calculator_agent,
        }

        query = "Some unrelated query about quantum physics"
        selected = keyword_selector.select_agent(query, agents)

        assert selected is None

    def test_select_agent_returns_none_no_keyword_matches(
        self,
        keyword_selector,
        weather_agent,
        calculator_agent
    ):
        """Test that no agent selected when query has no matching keywords"""
        agents = {
            weather_agent.agent_id: weather_agent,
            calculator_agent.agent_id: calculator_agent,
        }

        query = "xyz abc def"
        selected = keyword_selector.select_agent(query, agents)

        assert selected is None

    def test_select_agent_with_empty_agent_list(
        self,
        keyword_selector
    ):
        """Test select_agent with empty agent list"""
        agents = {}
        query = "Any query"

        selected = keyword_selector.select_agent(query, agents)

        assert selected is None

    def test_select_agent_with_single_agent(
        self,
        keyword_selector,
        weather_agent
    ):
        """Test select_agent with single agent"""
        agents = {
            weather_agent.agent_id: weather_agent
        }

        query = "What's the weather?"
        selected = keyword_selector.select_agent(query, agents)

        assert selected == weather_agent

    def test_select_agent_selects_highest_score(
        self,
        keyword_selector,
        weather_agent,
        calculator_agent
    ):
        """Test that the agent with highest score is selected"""
        agents = {
            weather_agent.agent_id: weather_agent,
            calculator_agent.agent_id: calculator_agent,
        }

        query = "weather weather weather calculate"
        selected = keyword_selector.select_agent(query, agents)

        assert selected == weather_agent

    def test_select_agent_with_multi_capability_agent(
        self,
        keyword_selector,
        multi_capability_agent
    ):
        """Test agent selection with multiple capabilities"""
        agents = {
            multi_capability_agent.agent_id: multi_capability_agent
        }

        query = "What time is it?"
        selected = keyword_selector.select_agent(query, agents)

        assert selected == multi_capability_agent

    def test_select_agent_best_capability_wins(
        self,
        keyword_selector,
        multi_capability_agent
    ):
        """Test that best capability score is used for agent"""
        agents = {
            multi_capability_agent.agent_id: multi_capability_agent
        }

        query = "weather temperature time"
        selected = keyword_selector.select_agent(query, agents)

        assert selected == multi_capability_agent

    def test_select_agent_empty_query(
        self,
        keyword_selector,
        weather_agent
    ):
        """Test with empty query string"""
        agents = {
            weather_agent.agent_id: weather_agent
        }

        selected = keyword_selector.select_agent("", agents)

        assert selected is None

    def test_select_agent_whitespace_query(
        self,
        keyword_selector,
        weather_agent
    ):
        """Test with whitespace-only query"""
        agents = {
            weather_agent.agent_id: weather_agent
        }

        selected = keyword_selector.select_agent("   ", agents)

        assert selected is None

        