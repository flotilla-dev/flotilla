# tests/test_llm_provider.py
import pytest
from unittest.mock import patch, MagicMock

from llm.llm_provider import LLMProvider


@pytest.fixture
def mock_settings(monkeypatch):
    """Fixture to override Settings with dummy test values."""
    monkeypatch.setenv("APP_OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("APP_OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("APP_OPENAI_TEMPERATURE", "0.1")



def test_get_llm_returns_chatopenai_instance(mock_settings):
    """Test that getLLM() returns a ChatOpenAI instance."""
    with patch("llm.llm_provider.ChatOpenAI") as mock_chat:
        mock_chat.return_value = MagicMock(name="MockChatOpenAI")

        provider = LLMProvider()
        llm = provider.get_llm()

        assert llm is mock_chat.return_value
        assert isinstance(llm, MagicMock)
