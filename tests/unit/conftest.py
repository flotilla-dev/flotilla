"""
Pytest configuration and shared fixtures
"""
import os
import sys
import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
from langgraph.checkpoint.memory import InMemorySaver

from config.settings import Settings, FlotillaSettings, ApplicationSettings

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_models import (
    LLMConfig,
    ToolRegistryConfig,
    AgentRegistryConfig,
    ClientConfig,
    OrchestrationConfig,
    OpenAIConfig,
    BusinessAgentConfg
)



@pytest.fixture
def mock_llm_config():
    return OpenAIConfig(
        api_key="test-key",
        model_name="gpt-4o-mini",
        temperature=0.3,
        max_tokens=1000
    )

@pytest.fixture
def mock_tool_registry_config():
    return dummy_tool_registry_config()

def dummy_tool_registry_config() -> ToolRegistryConfig:
    return ToolRegistryConfig(
        tool_packages=["tests.unit.tools"],
        tool_discovery=True,
        tool_recursive=True,
        settings=dummy_settings()
    )

@pytest.fixture
def mock_settings():
    return dummy_settings()


def dummy_settings() -> Settings:
    return Settings(
        flotilla=dummy_flotilla_settings(),
        application=ApplicationSettings(
            agent_configs={
                "Test Agent": {"foo": "bar"},
                "Agent 1": {"threshold": 0.7},
            }
        ),
    )

def dummy_flotilla_settings() -> FlotillaSettings:
    return FlotillaSettings(
        LLM__API_KEY="mock-key",
        LLM__MODEL="mock-model",
        LLM__TEMPERATURE="1",
        LLM__TYPE="openai",
        TOOL_REGISTRY__PACKAGES=["tools"],
        AGENT_REGISTRY__PACKAGES=["agents"]
    )

@pytest.fixture
def mock_agent_registry_config():
    return dummy_agent_registry_config()

def dummy_agent_registry_config() -> AgentRegistryConfig:
    return AgentRegistryConfig( 
        agent_discovery=False,
        agent_packages=["tests.unit.agents"],
        agent_recursive=False,
        llm_config=OpenAIConfig(api_key="test-key", model_name="gpt"),
        settings = dummy_settings()
    )

@pytest.fixture
def mock_business_agent_config():
    return BusinessAgentConfg(
        llm_config=OpenAIConfig(api_key="test-key", temperature=0.1, model_name="gpt-4"),
        checkpointer=InMemorySaver(),
        agent_configuration={}
    )

@pytest.fixture
def mock_orchestration_config():
    return OrchestrationConfig(
        llm_config=OpenAIConfig(api_key="test-key", temperature=0.1, model_name="gpt-4"),
        client=ClientConfig(client_id="test_client", client_name="Test Client"),
        tool_registry_config=dummy_tool_registry_config(),
        agent_registry_config=dummy_agent_registry_config()
    )

@pytest.fixture
def mock_llm():
    """Mock LangChain LLM"""
    llm = MagicMock()
    llm.invoke = Mock(return_value=MagicMock(content='{"test": "response"}'))
    return llm


@pytest.fixture
def mock_llm_with_text():
    """Mock LLM that returns plain text"""
    llm = MagicMock()
    llm.invoke = Mock(return_value=MagicMock(content="Test response"))
    return llm

@pytest.fixture
def mock_tool_registry():
    """Mock Tool Registry that does nothing"""
    tool_registry = MagicMock()
    tool_registry.get_all_tools.return_value = []
    tool_registry.get_tools.side_effect = lambda fn: list(filter(fn, tool_registry.get_all_tools()))
    return tool_registry



@pytest.fixture(autouse=True, scope="session")
def reset_environment():
    """Reset environment variables before each test"""
    # Store original env vars
    original_env = os.environ.copy()
    
    # Clear test-related env vars
    test_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "BLOCK_ACCESS_TOKEN",
        "LOG_LEVEL"
    ]
    for var in test_vars:
        os.environ.pop(var, None)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir