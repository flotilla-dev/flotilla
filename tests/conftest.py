"""
Pytest configuration and shared fixtures
"""
import os
import sys
import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_models import (
    LLMConfig,
    ToolRegistryConfig,
    AgentRegistryConfig,
    ClientConfig,
    OrchestrationConfig
)

from config.settings import Settings

settings = Settings()

@pytest.fixture
def mock_llm_config():
    return settings.get_llm_config()

@pytest.fixture
def mock_tool_registry_config():
    return ToolRegistryConfig(
        tool_packages=["tests.tools"],
        tool_discovery=True,
        tool_recursive=True
    )

@pytest.fixture
def mock_agent_registry_config():
    return AgentRegistryConfig(
        agent_discovery=False,
        agent_packages=["tests.agents"],
        agent_recursive=False,
        llm_config=settings.get_llm_config()
    )

@pytest.fixture
def mock_orchestration_config():
    return settings.get_orchestration_config()

'''
@pytest.fixture
def mock_azure_openai_config():
    """Mock Azure OpenAI configuration"""
    return AzureOpenAIConfig(
        endpoint="https://test-resource.openai.azure.com/",
        api_key="test-api-key",
        api_version="2024-02-15-preview",
        deployment_name="gpt-4",
        temperature=0.7,
        max_tokens=2000
    )


@pytest.fixture
def mock_fabric_workspace_config():
    """Mock Fabric workspace configuration"""
    return FabricWorkspaceConfig(
        workspace_id="test-workspace-id",
        lakehouse_id="test-lakehouse-id",
        lakehouse_name="test_lakehouse",
        endpoint="https://api.fabric.microsoft.com/v1",
        tenant_id="test-tenant-id"
    )


@pytest.fixture
def mock_block_mcp_config():
    """Mock Block MCP configuration"""
    return BlockMCPConfig(
        server_command="npx",
        server_args=["-y", "@modelcontextprotocol/server-square"],
        access_token="test-access-token",
        environment="sandbox",
        timeout=30
    )


@pytest.fixture
def mock_client_config(
    mock_azure_openai_config,
    mock_fabric_workspace_config,
    mock_block_mcp_config
):
    """Mock client configuration"""
    return ClientConfig(
        client_id="test_client_001",
        client_name="Test Client",
        azure_openai=mock_azure_openai_config,
        fabric_workspace=mock_fabric_workspace_config,
        block_mcp=mock_block_mcp_config,
        metadata={"industry": "test", "region": "test_region"}
    )


@pytest.fixture
def mock_orchestration_config(mock_client_config):
    """Mock orchestration configuration"""
    return OrchestrationConfig(
        client=mock_client_config,
        log_level="INFO",
        enable_tracing=True,
        max_retries=3,
        retry_delay=1.0
    )

'''

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