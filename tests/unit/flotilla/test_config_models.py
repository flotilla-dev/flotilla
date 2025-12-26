"""
Tests for configuration models
"""
import pytest
from pydantic import ValidationError

from flotilla.config_models import (
    LLMConfig,
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


