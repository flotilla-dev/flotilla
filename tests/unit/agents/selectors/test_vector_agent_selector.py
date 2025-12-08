"""
PyTest suite for VectorAgentSelector
"""
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from agents.selectors.vector_agent_selector import VectorAgentSelector
from agents.base_business_agent import BaseBusinessAgent, AgentCapability
from config.config_models import VectorAgentSelectorConfig


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_embeddings():
    """Mock LangChain Embeddings model"""
    embeddings = Mock()
    
    # Mock embed_query to return a simple vector
    def mock_embed_query(text):
        # Return deterministic vectors based on text content
        if "weather" in text.lower():
            return [1.0, 0.0, 0.0, 0.0]  # Weather vector
        elif "math" in text.lower() or "calculate" in text.lower():
            return [0.0, 1.0, 0.0, 0.0]  # Math vector
        elif "schedule" in text.lower() or "calendar" in text.lower():
            return [0.0, 0.0, 1.0, 0.0]  # Calendar vector
        else:
            return [0.0, 0.0, 0.0, 1.0]  # Generic vector
    
    # Mock embed_documents to handle batch
    def mock_embed_documents(texts):
        return [mock_embed_query(text) for text in texts]
    
    embeddings.embed_query = Mock(side_effect=mock_embed_query)
    embeddings.embed_documents = Mock(side_effect=mock_embed_documents)
    
    return embeddings


@pytest.fixture
def mock_config(mock_embeddings):
    """Mock VectorAgentSelectorConfig"""
    config = Mock(spec=VectorAgentSelectorConfig)
    config.embedding_model = mock_embeddings
    config.min_confidence = 0.5
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
def vector_selector(mock_config):
    """Create VectorAgentSelector instance"""
    return VectorAgentSelector(mock_config)


# ==========================================
# Constructor Tests
# ==========================================

def test_constructor_with_valid_config(mock_config):
    """Test constructor with valid config"""
    selector = VectorAgentSelector(mock_config)
    
    assert selector.selector_name == "VectorAgentSelector"
    assert selector.embeddings == mock_config.embedding_model
    assert selector.config == mock_config


def test_constructor_with_invalid_config():
    """Test constructor raises TypeError with invalid config"""
    invalid_config = {"embedding_model": Mock()}
    
    with pytest.raises(TypeError, match="VectorAgentSelector requires an instance of VectorAgentSelectorConfig"):
        VectorAgentSelector(invalid_config)


# ==========================================
# select_agent Tests
# ==========================================

def test_select_agent_finds_weather_agent(vector_selector, weather_agent, calculator_agent, calendar_agent):
    """Test that weather query selects weather agent"""
    agents = {weather_agent.agent_id: weather_agent, 
              calculator_agent.agent_id: calculator_agent, 
              calendar_agent.agent_id: calendar_agent
    }
    query = "What's the weather like today?"
    
    selected = vector_selector.select_agent(query, agents)
    
    assert selected == weather_agent
    assert vector_selector.embeddings.embed_query.called


def test_select_agent_finds_calculator_agent(vector_selector, weather_agent, calculator_agent, calendar_agent):
    """Test that math query selects calculator agent"""
    agents = {weather_agent.agent_id: weather_agent, 
              calculator_agent.agent_id: calculator_agent, 
              calendar_agent.agent_id: calendar_agent
    }
    query = "Calculate 15 times 23"
    
    selected = vector_selector.select_agent(query, agents)
    
    assert selected == calculator_agent


def test_select_agent_finds_calendar_agent(vector_selector, weather_agent, calculator_agent, calendar_agent):
    """Test that schedule query selects calendar agent"""
    agents = {weather_agent.agent_id: weather_agent, 
              calculator_agent.agent_id: calculator_agent, 
              calendar_agent.agent_id: calendar_agent
    }
    query = "Schedule a meeting for tomorrow"
    
    selected = vector_selector.select_agent(query, agents)
    
    assert selected == calendar_agent


def test_select_agent_returns_none_below_threshold(vector_selector, weather_agent, calculator_agent):
    """Test that no agent is selected if all scores below threshold"""
    # Set high threshold
    vector_selector.config.min_confidence = 0.99
    
    agents = {weather_agent.agent_id: weather_agent, 
              calculator_agent.agent_id: calculator_agent
    }
    query = "Some unrelated query about quantum physics"
    
    selected = vector_selector.select_agent(query, agents)
    
    assert selected is None


def test_select_agent_with_empty_agent_list(vector_selector):
    """Test select_agent with empty agent list"""
    agents = {}
    query = "Any query"
    
    selected = vector_selector.select_agent(query, agents)
    
    assert selected is None


def test_select_agent_with_single_agent(vector_selector, weather_agent):
    """Test select_agent with single agent"""
    agents = {weather_agent.agent_id: weather_agent    }
    query = "What's the weather?"
    
    selected = vector_selector.select_agent(query, agents)
    
    assert selected == weather_agent


def test_select_agent_selects_highest_score(vector_selector, mock_embeddings):
    """Test that the agent with highest score is selected"""
    # Create two agents with different similarity scores
    agent1 = Mock(spec=BaseBusinessAgent)
    agent1.agent_id = "agent1"
    agent1.agent_name = "Agent 1"
    agent1.get_capabilities = Mock(return_value=[
        AgentCapability(name="Cap1", description="weather info", keywords=["weather"], examples=[])
    ])
    
    agent2 = Mock(spec=BaseBusinessAgent)
    agent2.agent_id = "agent2"
    agent2.agent_name = "Agent 2"
    agent2.get_capabilities = Mock(return_value=[
        AgentCapability(name="Cap2", description="other stuff", keywords=["other"], examples=[])
    ])
    
    agents = {agent1.agent_id: agent1, 
              agent2.agent_id: agent2}
    query = "What's the weather?"  # Should match agent1 better
    
    selected = vector_selector.select_agent(query, agents)
    
    assert selected == agent1


# ==========================================
# _build_combined_agent_text Tests
# ==========================================

def test_build_combined_agent_text_basic(vector_selector, weather_agent):
    """Test building combined text from agent capabilities"""
    text = vector_selector._build_combined_agent_text(weather_agent)
    
    assert "Agent: Weather Agent" in text
    assert "Capability: Weather Forecast" in text
    assert "Description: Provides weather forecasts" in text
    assert "Keywords: weather, temperature, forecast, rain, climate" in text
    assert "Examples: What's the weather today? | Will it rain tomorrow?" in text


def test_build_combined_agent_text_with_empty_keywords(vector_selector):
    """Test building text when keywords are empty"""
    agent = Mock(spec=BaseBusinessAgent)
    agent.agent_name = "Test Agent"
    agent.get_capabilities = Mock(return_value=[
        AgentCapability(name="Test", description="Test desc", keywords=[], examples=["Ex1"])
    ])
    
    text = vector_selector._build_combined_agent_text(agent)
    
    assert "Agent: Test Agent" in text
    assert "Keywords:" not in text  # Should not include empty keywords


def test_build_combined_agent_text_with_empty_examples(vector_selector):
    """Test building text when examples are empty"""
    agent = Mock(spec=BaseBusinessAgent)
    agent.agent_name = "Test Agent"
    agent.get_capabilities = Mock(return_value=[
        AgentCapability(name="Test", description="Test desc", keywords=["key1"], examples=[])
    ])
    
    text = vector_selector._build_combined_agent_text(agent)
    
    assert "Agent: Test Agent" in text
    assert "Examples:" not in text  # Should not include empty examples


def test_build_combined_agent_text_multiple_capabilities(vector_selector):
    """Test building text with multiple capabilities"""
    agent = Mock(spec=BaseBusinessAgent)
    agent.agent_name = "Multi Agent"
    agent.get_capabilities = Mock(return_value=[
        AgentCapability(name="Cap1", description="First", keywords=["k1"], examples=["e1"]),
        AgentCapability(name="Cap2", description="Second", keywords=["k2"], examples=["e2"])
    ])
    
    text = vector_selector._build_combined_agent_text(agent)
    
    assert "Capability: Cap1" in text
    assert "Capability: Cap2" in text
    assert "First" in text
    assert "Second" in text


# ==========================================
# _vectorize_text Tests
# ==========================================

def test_vectorize_text_returns_normalized_array(vector_selector):
    """Test that _vectorize_text returns normalized numpy array"""
    text = "Sample text"
    
    result = vector_selector._vectorize_text(text)
    
    assert isinstance(result, np.ndarray)
    # Check normalization (L2 norm should be 1.0)
    norm = np.linalg.norm(result)
    assert np.isclose(norm, 1.0)


def test_vectorize_text_calls_embed_query(vector_selector):
    """Test that _vectorize_text calls embeddings.embed_query"""
    text = "Sample text"
    
    vector_selector._vectorize_text(text)
    
    vector_selector.embeddings.embed_query.assert_called_once_with(text=text)


def test_vectorize_text_handles_different_inputs(vector_selector):
    """Test vectorize_text with different input texts"""
    texts = ["weather query", "math query", "calendar query"]
    
    vectors = [vector_selector._vectorize_text(text) for text in texts]
    
    # All should be normalized
    for vec in vectors:
        assert np.isclose(np.linalg.norm(vec), 1.0)
    
    # Vectors should be different (not identical)
    assert not np.allclose(vectors[0], vectors[1])


# ==========================================
# _vectorize_texts Tests
# ==========================================

def test_vectorize_texts_returns_matrix(vector_selector):
    """Test that _vectorize_texts returns normalized matrix"""
    texts = ["text1", "text2", "text3"]
    
    result = vector_selector._vectorize_texts(texts)
    
    assert isinstance(result, np.ndarray)
    assert result.shape[0] == 3  # 3 texts
    assert result.ndim == 2  # Should be 2D matrix


def test_vectorize_texts_normalized_rows(vector_selector):
    """Test that each row in the matrix is normalized"""
    texts = ["weather text", "math text", "calendar text"]
    
    result = vector_selector._vectorize_texts(texts)
    
    # Check each row is normalized
    row_norms = np.linalg.norm(result, axis=1)
    assert np.allclose(row_norms, 1.0)


def test_vectorize_texts_calls_embed_documents(vector_selector):
    """Test that _vectorize_texts calls embeddings.embed_documents"""
    texts = ["text1", "text2"]
    
    vector_selector._vectorize_texts(texts)
    
    vector_selector.embeddings.embed_documents.assert_called_once_with(texts)


def test_vectorize_texts_single_text(vector_selector):
    """Test _vectorize_texts with single text in list"""
    texts = ["single text"]
    
    result = vector_selector._vectorize_texts(texts)
    
    assert result.shape[0] == 1
    assert np.isclose(np.linalg.norm(result[0]), 1.0)


def test_vectorize_texts_empty_list(vector_selector):
    """Test _vectorize_texts with empty list"""
    texts = []
    
    result = vector_selector._vectorize_texts(texts)
    
    assert isinstance(result, np.ndarray)
    assert result.shape[0] == 0


# ==========================================
# Integration Tests
# ==========================================

def test_end_to_end_agent_selection(mock_config, weather_agent, calculator_agent, calendar_agent):
    """Test complete end-to-end agent selection flow"""
    selector = VectorAgentSelector(mock_config)
    agents = {weather_agent.agent_id: weather_agent, 
              calculator_agent.agent_id: calculator_agent, 
              calendar_agent.agent_id: calendar_agent
    }
    
    # Test multiple queries
    test_cases = [
        ("What's the weather?", weather_agent),
        ("Calculate 5 + 5", calculator_agent),
        ("Schedule a meeting", calendar_agent),
    ]
    
    for query, expected_agent in test_cases:
        selected = selector.select_agent(query, agents)
        assert selected == expected_agent, f"Failed for query: {query}"


def test_similarity_scores_are_compared_correctly(vector_selector, mock_embeddings):
    """Test that similarity scores are correctly compared"""
    # Create agents with known embeddings
    agent_high = Mock(spec=BaseBusinessAgent)
    agent_high.agent_name = "High Match"
    agent_high.agent_id = "high"
    agent_high.get_capabilities = Mock(return_value=[
        AgentCapability(name="C", description="weather stuff", keywords=["weather"], examples=[])
    ])
    
    agent_low = Mock(spec=BaseBusinessAgent)
    agent_low.agent_name = "Low Match"
    agent_low.agent_id = "low"
    agent_low.get_capabilities = Mock(return_value=[
        AgentCapability(name="C", description="other stuff", keywords=["other"], examples=[])
    ])
    
    agents = {agent_low.agent_id: agent_low, 
              agent_high.agent_id: agent_high
    }  # Low first to ensure comparison works
    query = "What's the weather?"
    
    selected = vector_selector.select_agent(query, agents)
    
    # Should select agent_high despite it being listed second
    assert selected == agent_high


# ==========================================
# Edge Cases
# ==========================================

def test_agent_with_no_capabilities(vector_selector):
    """Test handling agent with no capabilities"""
    agent = Mock(spec=BaseBusinessAgent)
    agent.agent_name = "Empty Agent"
    agent.get_capabilities = Mock(return_value=[])
    
    text = vector_selector._build_combined_agent_text(agent)
    
    assert "Agent: Empty Agent" in text


def test_confidence_threshold_boundary(vector_selector, weather_agent):
    """Test selection at exact confidence threshold"""
    # Set threshold to exact match value
    vector_selector.config.min_confidence = 1.0
    
    agents = {weather_agent.agent_id: weather_agent}
    query = "weather"  # Should be exact match
    
    selected = vector_selector.select_agent(query, agents)
    
    assert selected == weather_agent
