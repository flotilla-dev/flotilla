"""
Tests for configuration models
"""
import pytest
from pydantic import ValidationError

from config.config_models import (
    LLMConfig,
    ToolRegistryConfig,
    AgentRegistryConfig,
    OrchestrationConfig,
    OpenAIConfig,
    AzureOpenAIConfig
)


class TestLLMConfig:
    def test_valid_config_creation(self):
        """Should create an LLMConfig with all required fields."""
        config = LLMConfig(
            api_key="sk-test-key",
            temperature=0.2,
            max_tokens=1500
        )

        assert config.api_key == "sk-test-key"
        assert config.temperature == 0.2
        assert config.max_tokens == 1500

    def test_valid_openai_config_creation(self):
        config = OpenAIConfig(
            api_key="sk-test-key",
            model_name="gpt-4o-mini",
            temperature=0.3,
            max_tokens=1000
        )

        assert config.api_key == "sk-test-key"
        assert config.model_name == "gpt-4o-mini"
        assert config.temperature == 0.3
        assert config.max_tokens == 1000

    def test_defaults_are_applied(self):
        """Should apply default model_name, temperature, and max_tokens when omitted."""
        config = LLMConfig(
            api_key="sk-123"
        )

        assert config.temperature == 0.1
        assert config.max_tokens == 2000

    def test_missing_required_fields_raises_error(self):
        """Should raise ValidationError when required fields are missing."""
        with pytest.raises(ValidationError) as exc:
            LLMConfig()

        # Check that both endpoint and api_key are mentioned in errors
        errors = str(exc.value)
        #assert "endpoint" in errors
        assert "api_key" in errors

    def test_invalid_temperature_type_raises_error(self):
        """Should raise ValidationError if temperature is not a float."""
        with pytest.raises(ValidationError):
            LLMConfig(
                #endpoint="https://api.fake.com",
                api_key="sk-test",
                temperature="hot"  # invalid type
            )

    def test_optional_max_tokens_can_be_none(self):
        """Should allow max_tokens to be None."""
        config = LLMConfig(
            endpoint="https://api.fake.com",
            api_key="sk-test",
            max_tokens=None
        )
        assert config.max_tokens is None



class TestToolRegistryConfig:
    def test_valid_config_creation(self, mock_settings):
        """Should create a valid ToolRegistryConfig with required fields."""
        config = ToolRegistryConfig(
            tool_packages=["tools.common", "tools.math"],
            tool_recursive=True,
            settings=mock_settings
        )

        assert config.tool_packages == ["tools.common", "tools.math"]
        assert config.tool_recursive is True

    def test_default_recursive_is_true(self, mock_settings):
        """Should default tool_recursive to True when not specified."""
        config = ToolRegistryConfig(tool_packages=["tools.ai"], settings=mock_settings)
        assert config.tool_recursive is True  # pydantic should coerce "true" → True


    def test_tool_packages_must_be_list_of_strings(self):
        """Should raise ValidationError if tool_packages is not a list of strings."""
        with pytest.raises(ValidationError):
            ToolRegistryConfig(tool_packages="not-a-list")  # invalid type


class TestAgentRegistryConfig:
    def test_valid_config_creation(self, mock_settings, mock_llm_config):
        """Should create a valid AgentRegistryConfig with all required fields."""
        config = AgentRegistryConfig(
            agent_packages=["agents.sales", "agents.marketing"],
            agent_recursive=True,
            llm_config=mock_llm_config,
            settings=mock_settings
        )

        assert config.agent_packages == ["agents.sales", "agents.marketing"]
        assert config.agent_recursive is True
        assert config.llm_config is not None
        assert isinstance(config.llm_config, LLMConfig)
        assert config.settings is not None
        assert config.llm_config.api_key == "test-key"

    def test_default_recursive_true(self, mock_settings):
        """Should default agent_recursive to True when not specified."""
        llm_cfg = LLMConfig(
            endpoint="https://example.com/llm",
            api_key="sk-test"
        )

        config = AgentRegistryConfig(
            agent_packages=["agents.customer"],
            llm_config=llm_cfg,
            settings=mock_settings
        )

        assert config.agent_recursive is True


    def test_invalid_llm_config_type_raises_error(self):
        """Should raise ValidationError if llm_config is not an LLMConfig."""
        with pytest.raises(ValidationError):
            AgentRegistryConfig(
                agent_packages=["agents.ai"],
                llm_config="not-an-llm-config"
            )

    def test_nested_llm_config_defaults_apply(self, mock_settings):
        """Should preserve LLMConfig defaults when nested inside AgentRegistryConfig."""
        llm_cfg = LLMConfig(
            api_key="sk-123"
        )

        config = AgentRegistryConfig(
            agent_packages=["agents.test"],
            llm_config=llm_cfg,
            settings=mock_settings
        )

        assert config.llm_config.temperature == 0.1
        assert config.llm_config.max_tokens == 2000