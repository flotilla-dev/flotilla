"""
Pytest tests for ConfigFactory
"""
import pytest
from unittest.mock import Mock, patch
from config.config_factory import ConfigFactory
from config.settings import Settings
from config.flotilla_setttings import FlotillaSettings, LLMType
from config.application_settings import ApplicationSettings
from config.config_loader import ConfigLoader
from config.config_models import (
    LLMConfig,
    OpenAIConfig,
    AzureOpenAIConfig,
    ToolRegistryConfig,
    AgentRegistryConfig,
    OrchestrationConfig,
    ClientConfig
)


@pytest.fixture
def mock_settings():
    """Create a mock Settings object with default values"""
    flotilla_settings = FlotillaSettings(
        LLM__API_KEY="test-api-key",
        LLM__MODEL= "gpt-4o-mini",
        LLM__TEMPERATURE=0.1,
        LLM__TYPE=LLMType.OPENAI,
        LOG__LEVEL="INFO",
        TOOL_REGISTRY__ENABLE_DISCOVERY=True,
        TOOL_REGISTRY__RECURISVE=True,
        TOOL_REGISTRY__PACKAGES=["tools"],
        AGENT_REGISTRY__ENABLE_DISCOVERY=True,
        AGENT_REGISTRY__RECURSIVE=True,
        AGENT_REGISTRY__PACKAGES=["agents.business_logic"]
    )
    application_settings = ApplicationSettings(
        agent_configs={},
        tool_configs={}, 
        feature_flags={}
    )
    
    return Settings(flotilla=flotilla_settings, application=application_settings)


class TestLLMConfigCreation:
    """Tests for LLM configuration creation"""
    
    def test_create_openai_config(self, mock_settings):
        """Test creation of OpenAI configuration"""
        config = ConfigFactory._create_openai_config(mock_settings)
        
        assert isinstance(config, OpenAIConfig)
        assert config.api_key == "test-api-key"
        assert config.model_name == "gpt-4o-mini"
        assert config.temperature == 0.1
    
    '''
    def test_create_azure_openai_config(self, mock_settings):
        """Test creation of Azure OpenAI configuration"""
        mock_settings.LLM__TYPE = LLMType.AZURE_OPENAI
        mock_settings.AZURE__ENDPOINT = "https://test.openai.azure.com"
        mock_settings.AZURE__API_VERSION = "2024-02-15-preview"
        mock_settings.AZURE__DEPLOYMENT_NAME = "gpt-4-deployment"
        
        factory = ConfigFactory(mock_settings)
        config = factory.create_llm_config()
        
        assert isinstance(config, AzureOpenAIConfig)
        assert config.api_key == "test-api-key"
        assert config.endpoint == "https://test.openai.azure.com"
        assert config.api_version == "2024-02-15-preview"
        assert config.deployment_name == "gpt-4-deployment"
        assert config.temperature == 0.1

        
    def test_azure_config_with_defaults(self, mock_settings):
        """Test Azure config uses defaults when optional values not provided"""
        mock_settings.LLM__TYPE = LLMType.AZURE_OPENAI
        mock_settings.AZURE__ENDPOINT = "https://test.openai.azure.com"
        
        factory = ConfigFactory(mock_settings)
        config = factory.create_llm_config()
        
        assert config.api_version == "2024-02-15-preview"
        assert config.deployment_name == "gpt-4"
    
    def test_azure_config_missing_endpoint_raises_error(self, mock_settings):
        """Test that missing Azure endpoint raises ValueError"""
        mock_settings.LLM__TYPE = LLMType.AZURE_OPENAI
        
        factory = ConfigFactory(mock_settings)
        
        with pytest.raises(ValueError, match="Azure endpoint not configured"):
            factory.create_llm_config()
        '''
    
    def test_unsupported_llm_type_raises_error(self, mock_settings):
        """Test that unsupported LLM type raises ValueError"""
        mock_settings.flotilla.LLM__TYPE = "unsupported_type"
        
        
        
        with pytest.raises(ValueError, match="Unsupported LLM type"):
            ConfigFactory.create_llm_config(mock_settings)

    

    def test_temperature_string_conversion(self, mock_settings):
        """Test that temperature string is converted to float"""
        config = ConfigFactory.create_llm_config(mock_settings)
        assert isinstance(config.temperature, float)
        assert config.temperature == 0.1


class TestToolRegistryConfigCreation:
    """Tests for Tool Registry configuration creation"""
    
    def test_create_tool_registry_config(self, mock_settings):
        """Test creation of tool registry configuration"""
        config = ConfigFactory.create_tool_registry_config(mock_settings)
        
        assert isinstance(config, ToolRegistryConfig)
        assert config.tool_discovery is True
        assert config.tool_packages == ["tools"]
        assert config.tool_recursive is True
    

    def test_tool_registry_config_disabled_discovery(self, mock_settings):
        """Test tool registry config with discovery disabled"""
        mock_settings.flotilla.TOOL_REGISTRY__ENABLE_DISCOVERY = False
        config = ConfigFactory.create_tool_registry_config(mock_settings)
        assert config.tool_discovery is False

    
    def test_tool_registry_config_multiple_packages(self, mock_settings):
        """Test tool registry config with multiple packages"""
        mock_settings.flotilla.TOOL_REGISTRY__PACKAGES = ["tools", "custom_tools", "plugins"]
        
        config = ConfigFactory.create_tool_registry_config(mock_settings)
        
        assert len(config.tool_packages) == 3
        assert "custom_tools" in config.tool_packages


class TestAgentRegistryConfigCreation:
    """Tests for Agent Registry configuration creation"""
    
    def test_create_agent_registry_config(self, mock_settings):
        """Test creation of agent registry configuration"""
        config = ConfigFactory.create_agent_registry_config(mock_settings)

        assert isinstance(config, AgentRegistryConfig)
        assert config.agent_discovery is True
        assert config.agent_packages == ["agents.business_logic"]
        assert config.agent_recursive is True
        assert isinstance(config.llm_config, OpenAIConfig)
    
    def test_agent_registry_config_contains_llm_config(self, mock_settings):
        """Test that agent registry config includes LLM configuration"""
        config = ConfigFactory.create_agent_registry_config(mock_settings)
        
        assert config.llm_config.api_key == "test-api-key"
        assert config.llm_config.model_name == "gpt-4o-mini"
    
    def test_agent_registry_config_disabled_discovery(self, mock_settings):
        """Test agent registry config with discovery disabled"""
        mock_settings.flotilla.AGENT_REGISTRY__ENABLE_DISCOVERY = False
        
        config = ConfigFactory.create_agent_registry_config(mock_settings)
        
        assert config.agent_discovery is False


class TestClientConfigCreation:
    """Tests for Client configuration creation"""
    
    def test_create_client_config_defaults(self, mock_settings):
        """Test creation of client config with default values"""
        config = ConfigFactory.create_client_config(mock_settings)
        
        assert isinstance(config, ClientConfig)
        assert config.client_id == "test_1"
        assert config.client_name == "Test"
        assert config.metadata == {}
    
    '''
    def test_create_client_config_custom_values(self, mock_settings):
        """Test creation of client config with custom values"""
        metadata = {"environment": "production", "region": "us-east-1"}
        
        mock_settings.

        config = config_factory.create_client_config(
            client_id="prod_123",
            client_name="Production Client",
            metadata=metadata
        )
        
        assert config.client_id == "prod_123"
        assert config.client_name == "Production Client"
        assert config.metadata == metadata
    '''
        
    def test_create_client_config_empty_metadata(self, mock_settings):
        """Test that None metadata defaults to empty dict"""
        config = ConfigFactory.create_client_config(mock_settings)
        
        assert config.metadata == {}


class TestOrchestrationConfigCreation:
    """Tests for Orchestration configuration creation"""
    
    def test_create_orchestration_config_defaults(self, mock_settings):
        """Test creation of orchestration config with defaults"""
        config = ConfigFactory.create_orchestration_config(mock_settings)
        
        assert isinstance(config, OrchestrationConfig)
        assert config.log_level == "INFO"
        assert isinstance(config.llm_config, OpenAIConfig)
        assert isinstance(config.client, ClientConfig)
        assert config.client.client_id == "test_1"
    
    '''
    def test_create_orchestration_config_custom_client(self, config_factory):
        """Test creation of orchestration config with custom client"""
        metadata = {"tier": "enterprise"}
        
        config = config_factory.create_orchestration_config(
            client_id="enterprise_456",
            client_name="Enterprise Client",
            client_metadata=metadata
        )
        
        assert config.client.client_id == "enterprise_456"
        assert config.client.client_name == "Enterprise Client"
        assert config.client.metadata == metadata
    '''


    def test_orchestration_config_log_level(self, mock_settings):
        """Test orchestration config respects log level setting"""
        mock_settings.flotilla.LOG__LEVEL = "DEBUG"
        
        config = ConfigFactory.create_orchestration_config(mock_settings)
        
        assert config.log_level == "DEBUG"


class TestEdgeCases:
    """Tests for edge cases and error conditions"""
    
    def test_empty_tool_packages(self, mock_settings):
        """Test behavior with empty tool packages list"""
        mock_settings.flotilla.TOOL_REGISTRY__PACKAGES = []
        
        config = ConfigFactory.create_tool_registry_config(mock_settings)
        
        assert config.tool_packages == []
    
    def test_empty_agent_packages(self, mock_settings):
        """Test behavior with empty agent packages list"""
        mock_settings.flotilla.AGENT_REGISTRY__PACKAGES = []
        config = ConfigFactory.create_agent_registry_config(mock_settings)        
        assert config.agent_packages == []
    
    def test_zero_temperature(self, mock_settings):
        """Test handling of zero temperature"""
        mock_settings.flotilla.LLM__TEMPERATURE = "0"
        
        config = ConfigFactory.create_llm_config(mock_settings)
        
        assert config.temperature == 0.0
    
    def test_high_temperature(self, mock_settings):
        """Test handling of high temperature value"""
        mock_settings.flotilla.LLM__TEMPERATURE = "2.0"

        config = ConfigFactory.create_llm_config(mock_settings)

        assert config.temperature == 2.0


class TestIntegration:
    """Integration tests with real Settings object"""
    

    def test_factory_with_real_settings(self, mock_settings):
        """Test factory works with actual Settings object"""
        config = ConfigFactory.create_llm_config(mock_settings)
        
        assert isinstance(config, OpenAIConfig)
        assert config.model_name == 'gpt-4o-mini'
    
    def test_multiple_config_creations(self, mock_settings):
        """Test that multiple config creations produce consistent results"""
        config1 = ConfigFactory.create_llm_config(mock_settings)
        config2 = ConfigFactory.create_llm_config(mock_settings)
        
        assert config1.api_key == config2.api_key
        assert config1.model_name == config2.model_name
        assert config1.temperature == config2.temperature


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
