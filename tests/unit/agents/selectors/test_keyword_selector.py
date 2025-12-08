"""
PyTest suite for KeywordAgentSelector
"""
import pytest
from unittest.mock import Mock
from agents.selectors.keyword_agent_selector import KeywordAgentSelector
from agents.base_business_agent import BaseBusinessAgent, AgentCapability
from config.config_models import KeywordAgentSelectorConfig


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_config():
    """Mock KeywordAgentSelectorConfig"""
    config = Mock(spec=KeywordAgentSelectorConfig)
    config.min_confidence = 0.2
    return config


@pytest.fixture
def weather_agent():
    """Create a mock weather agent"""
    agent = Mock(spec=BaseBusinessAgent)
    agent.agent_id = "weather_agent"
    agent.agent_name = "Weather Agent"
    
    capabilities = [
        AgentCapability(
            name="Weather Forecast",
            description="Provides weather forecasts and current conditions",
            keywords=["weather", "temperature", "forecast", "rain", "climate"],
            examples=["What's the weather today?", "Will it rain tomorrow?"]
        )
    ]
    agent.get_capabilities = Mock(return_value=capabilities)
    
    return agent


@pytest.fixture
def calculator_agent():
    """Create a mock calculator agent"""
    agent = Mock(spec=BaseBusinessAgent)
    agent.agent_id = "calculator_agent"
    agent.agent_name = "Calculator Agent"
    
    capabilities = [
        AgentCapability(
            name="Math Calculations",
            description="Performs mathematical calculations and equations",
            keywords=["math", "calculate", "equation", "arithmetic", "compute"],
            examples=["Calculate 25 * 48", "What is 15% of 200?"]
        )
    ]
    agent.get_capabilities = Mock(return_value=capabilities)
    
    return agent


@pytest.fixture
def calendar_agent():
    """Create a mock calendar agent"""
    agent = Mock(spec=BaseBusinessAgent)
    agent.agent_id = "calendar_agent"
    agent.agent_name = "Calendar Agent"
    
    capabilities = [
        AgentCapability(
            name="Schedule Management",
            description="Manages appointments, schedules, and events",
            keywords=["schedule", "calendar", "appointment", "meeting", "event"],
            examples=["Schedule a meeting", "What's on my calendar?"]
        )
    ]
    agent.get_capabilities = Mock(return_value=capabilities)
    
    return agent


@pytest.fixture
def multi_capability_agent():
    """Create agent with multiple capabilities"""
    agent = Mock(spec=BaseBusinessAgent)
    agent.agent_id = "multi_agent"
    agent.agent_name = "Multi Capability Agent"
    
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
    ]
    agent.get_capabilities = Mock(return_value=capabilities)
    
    return agent


@pytest.fixture
def keyword_selector(mock_config):
    """Create KeywordAgentSelector instance"""
    return KeywordAgentSelector(mock_config)


# ==========================================
# Constructor Tests
# ==========================================

def test_constructor_with_valid_config(mock_config):
    """Test constructor with valid config"""
    selector = KeywordAgentSelector(mock_config)
    
    assert selector.selector_name == "KeywordAgentSelector"
    assert selector.config == mock_config


def test_constructor_sets_name():
    """Test that constructor sets correct selector name"""
    config = Mock(spec=KeywordAgentSelectorConfig)
    selector = KeywordAgentSelector(config)
    
    assert selector.selector_name == "KeywordAgentSelector"


# ==========================================
# select_agent Tests
# ==========================================

def test_select_agent_finds_weather_agent(keyword_selector, weather_agent, calculator_agent, calendar_agent):
    keyword_selector.config
    """Test that weather query selects weather agent"""
    agents = {
        weather_agent.agent_id: weather_agent, 
        calculator_agent.agent_id: calculator_agent, 
        calendar_agent.agent_id: calendar_agent}
    query = "What's the weather like today?"
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected == weather_agent


def test_select_agent_finds_calculator_agent(keyword_selector, weather_agent, calculator_agent, calendar_agent):
    """Test that math query selects calculator agent"""
    agents = {
        weather_agent.agent_id: weather_agent, 
        calculator_agent.agent_id: calculator_agent, 
        calendar_agent.agent_id: calendar_agent
    }    

    query = "Calculate 15 times 23"
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected == calculator_agent


def test_select_agent_finds_calendar_agent(keyword_selector, weather_agent, calculator_agent, calendar_agent):
    """Test that schedule query selects calendar agent"""
    agents = {
        weather_agent.agent_id: weather_agent, 
        calculator_agent.agent_id: calculator_agent, 
        calendar_agent.agent_id: calendar_agent
    }
    query = "Schedule a meeting for tomorrow"
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected == calendar_agent


def test_select_agent_multiple_keyword_matches(keyword_selector, weather_agent):
    """Test query with multiple matching keywords"""
    agents = {
        weather_agent.agent_id: weather_agent
    }
    query = "What's the weather and temperature forecast today?"
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected == weather_agent


def test_select_agent_case_insensitive(keyword_selector, weather_agent):
    """Test that keyword matching is case insensitive"""
    agents = {
        weather_agent.agent_id: weather_agent
    }
    query = "WEATHER FORECAST"  # All caps
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected == weather_agent


def test_select_agent_partial_keyword_match(keyword_selector, calculator_agent):
    """Test that partial keyword matches work"""
    agents = {
        calculator_agent.agent_id: calculator_agent
    }
    query = "I need to calculate something"
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected == calculator_agent


def test_select_agent_returns_none_below_threshold(keyword_selector, weather_agent, calculator_agent):
    """Test that no agent is selected if all scores below threshold"""
    # Set high threshold
    keyword_selector.config.min_confidence = 0.99
    
    agents = {
        weather_agent.agent_id: weather_agent, 
        calculator_agent.agent_id: calculator_agent
    }
    query = "Some unrelated query about quantum physics"
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected is None


def test_select_agent_returns_none_no_keyword_matches(keyword_selector, weather_agent, calculator_agent):
    """Test that no agent selected when query has no matching keywords"""
    agents = {
        weather_agent.agent_id: weather_agent, 
        calculator_agent.agent_id: calculator_agent
    }
    query = "xyz abc def"  # No keywords match
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected is None


def test_select_agent_with_empty_agent_list(keyword_selector):
    """Test select_agent with empty agent list"""
    agents = {}
    query = "Any query"
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected is None


def test_select_agent_with_single_agent(keyword_selector, weather_agent):
    """Test select_agent with single agent"""
    agents = {
        weather_agent.agent_id: weather_agent
    }
    query = "What's the weather?"
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected == weather_agent


def test_select_agent_selects_highest_score(keyword_selector, weather_agent, calculator_agent):
    """Test that the agent with highest score is selected"""
    agents = {
        weather_agent.agent_id: weather_agent, 
        calculator_agent.agent_id: calculator_agent
    }
    query = "weather weather weather calculate"  # More weather keywords
    
    selected = keyword_selector.select_agent(query, agents)
    
    # Should select weather agent (3 weather matches vs 1 calculate match)
    assert selected == weather_agent


def test_select_agent_with_multi_capability_agent(keyword_selector, multi_capability_agent):
    """Test agent selection with multiple capabilities"""
    agents = {multi_capability_agent.agent_id: multi_capability_agent}
    query = "What time is it?"
    
    selected = keyword_selector.select_agent(query, agents)
    
    # Should match "time" keyword from second capability
    assert selected == multi_capability_agent


def test_select_agent_best_capability_wins(keyword_selector, multi_capability_agent):
    """Test that best capability score is used for agent"""
    agents = {multi_capability_agent.agent_id: multi_capability_agent}
    query = "weather temperature time"  # Matches both capabilities
    
    selected = keyword_selector.select_agent(query, agents)
    
    # Should select based on best capability match
    assert selected == multi_capability_agent


def test_select_agent_empty_query(keyword_selector, weather_agent):
    """Test with empty query string"""
    agents = {
        weather_agent.agent_id: weather_agent
    }
    query = ""
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected is None


def test_select_agent_whitespace_query(keyword_selector, weather_agent):
    """Test with whitespace-only query"""
    agents = {
        weather_agent.agent_id: weather_agent
    }
    query = "   "
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected is None


# ==========================================
# _match_keywords Tests
# ==========================================

def test_match_keywords_perfect_match(keyword_selector):
    """Test perfect keyword match returns 1.0"""
    keywords = ["weather", "forecast"]
    query = "weather forecast"
    
    score = keyword_selector._match_keywords(query, keywords)
    
    assert score == 1.0


def test_match_keywords_partial_match(keyword_selector):
    """Test partial keyword match returns correct fraction"""
    keywords = ["weather", "forecast", "temperature", "rain"]
    query = "weather forecast"  # Matches 2 out of 4
    
    score = keyword_selector._match_keywords(query, keywords)
    
    assert score == 0.5


def test_match_keywords_no_match(keyword_selector):
    """Test no keyword match returns 0.0"""
    keywords = ["weather", "forecast"]
    query = "calculate math"
    
    score = keyword_selector._match_keywords(query, keywords)
    
    assert score == 0.0


def test_match_keywords_case_insensitive(keyword_selector):
    """Test keyword matching is case insensitive"""
    keywords = ["Weather", "FORECAST"]
    query = "weather forecast"
    
    score = keyword_selector._match_keywords(query, keywords)
    
    assert score == 1.0


def test_match_keywords_substring_match(keyword_selector):
    """Test that keywords match as substrings"""
    keywords = ["calculate"]
    query = "I need to calculate something"
    
    score = keyword_selector._match_keywords(query, keywords)
    
    assert score == 1.0


def test_match_keywords_empty_keywords(keyword_selector):
    """Test with empty keyword list returns 0.0"""
    keywords = []
    query = "any query"
    
    score = keyword_selector._match_keywords(query, keywords)
    
    assert score == 0.0


def test_match_keywords_empty_query(keyword_selector):
    """Test with empty query returns 0.0"""
    keywords = ["weather", "forecast"]
    query = ""
    
    score = keyword_selector._match_keywords(query, keywords)
    
    assert score == 0.0


def test_match_keywords_single_keyword(keyword_selector):
    """Test with single keyword"""
    keywords = ["weather"]
    query = "weather"
    
    score = keyword_selector._match_keywords(query, keywords)
    
    assert score == 1.0


def test_match_keywords_multiple_occurrences(keyword_selector):
    """Test that multiple occurrences of same keyword count as one match"""
    keywords = ["weather", "forecast"]
    query = "weather weather weather forecast"
    
    score = keyword_selector._match_keywords(query, keywords)
    
    # Should be 1.0 (both keywords present, duplicates don't increase score)
    assert score == 1.0


def test_match_keywords_caps_scores_at_one(keyword_selector):
    """Test that score is capped at 1.0"""
    keywords = ["weather"]
    query = "weather forecast temperature"  # More words than keywords
    
    score = keyword_selector._match_keywords(query, keywords)
    
    assert score == 1.0
    assert score <= 1.0


def test_match_keywords_special_characters(keyword_selector):
    """Test keyword matching with special characters"""
    keywords = ["weather"]
    query = "weather! What's the forecast?"
    
    score = keyword_selector._match_keywords(query, keywords)
    
    assert score == 1.0


# ==========================================
# Integration Tests
# ==========================================

def test_end_to_end_agent_selection(mock_config, weather_agent, calculator_agent, calendar_agent):
    """Test complete end-to-end agent selection flow"""
    selector = KeywordAgentSelector(mock_config)
    agents = {
        weather_agent.agent_id: weather_agent, 
        calculator_agent.agent_id: calculator_agent, 
        calendar_agent.agent_id: calendar_agent
    }
    
    # Test multiple queries
    test_cases = [
        ("What's the weather?", weather_agent),
        ("Calculate 5 + 5", calculator_agent),
        ("Schedule a meeting", calendar_agent),
        ("weather and temperature", weather_agent),
        ("math equation", calculator_agent),
    ]
    
    for query, expected_agent in test_cases:
        selected = selector.select_agent(query, agents)
        assert selected == expected_agent, f"Failed for query: {query}"


def test_confidence_threshold_filtering(mock_config, weather_agent, calculator_agent):
    """Test that confidence threshold properly filters agents"""
    mock_config.min_confidence = 0.8  # High threshold
    selector = KeywordAgentSelector(mock_config)
    
    agents = {
        weather_agent.agent_id: weather_agent, 
        calculator_agent.agent_id: calculator_agent
    }
    
    # Query with weak match (only 1 of 5 keywords)
    query = "weather"  # Matches 1/5 keywords = 0.2 score
    selected = selector.select_agent(query, agents)
    
    assert selected is None  # Below 0.8 threshold


def test_multiple_agents_same_score(keyword_selector):
    """Test behavior when multiple agents have same score"""
    # Create two identical agents
    agent1 = Mock(spec=BaseBusinessAgent)
    agent1.agent_id = "agent1"
    agent1.agent_name = "Agent 1"
    agent1.get_capabilities = Mock(return_value=[
        AgentCapability(name="C1", description="D1", keywords=["weather"], examples=[])
    ])
    
    agent2 = Mock(spec=BaseBusinessAgent)
    agent2.agent_id = "agent2"
    agent2.agent_name = "Agent 2"
    agent2.get_capabilities = Mock(return_value=[
        AgentCapability(name="C2", description="D2", keywords=["weather"], examples=[])
    ])
    
    agents = {
        agent1.agent_id: agent1,
        agent2.agent_id: agent2
    }
    query = "weather"
    
    selected = keyword_selector.select_agent(query, agents)
    
    # Should select one of them (implementation selects last one with max score)
    assert selected in [agent1, agent2]


# ==========================================
# Edge Cases
# ==========================================

def test_agent_with_no_capabilities(keyword_selector):
    """Test handling agent with no capabilities"""
    agent = Mock(spec=BaseBusinessAgent)
    agent.agent_name = "Empty Agent"
    agent.agent_id = "empty_agent"
    agent.get_capabilities = Mock(return_value=[])
    
    agents = {agent.agent_id: agent}
    query = "any query"
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected is None


def test_agent_with_capability_no_keywords(keyword_selector):
    """Test agent with capability that has no keywords"""
    agent = Mock(spec=BaseBusinessAgent)
    agent.agent_name = "No Keywords Agent"
    agent.agent_id = "no_keywords_agent"
    agent.get_capabilities = Mock(return_value=[
        AgentCapability(name="Cap", description="Desc", keywords=[], examples=[])
    ])
    
    agents = {agent.agent_id: agent}
    query = "any query"
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected is None


def test_confidence_threshold_boundary(keyword_selector, weather_agent):
    """Test selection at exact confidence threshold"""
    keyword_selector.config.min_confidence = 0.2  # 1/5 keywords
    
    agents = {weather_agent.agent_id: weather_agent}
    query = "weather"  # Matches 1/5 keywords = 0.2
    
    selected = keyword_selector.select_agent(query, agents)
    
    # Should select because score >= threshold
    assert selected == weather_agent


def test_unicode_handling(keyword_selector):
    """Test handling of unicode characters"""
    agent = Mock(spec=BaseBusinessAgent)
    agent.agent_name = "Unicode Agent"
    agent.agent_id = "unicode_agent"
    agent.get_capabilities = Mock(return_value=[
        AgentCapability(name="C", description="D", keywords=["café", "naïve"], examples=[])
    ])
    
    agents = {agent.agent_id: agent}
    query = "café naïve"
    
    selected = keyword_selector.select_agent(query, agents)
    
    assert selected == agent
