# tests/test_llm_provider.py
import pytest

from llm.llm_factory import LLMFactory, AzureChatOpenAI, ChatOpenAI
from config.config_models import OpenAIConfig, AzureOpenAIConfig, LLMConfig




def test_openai_creation():
    config = OpenAIConfig(
        model_name="gpt-40-mini",
        api_key="test-key",
        temperature=0.1
    )
    llm_factory = LLMFactory()
    llm = llm_factory.get_llm(config)

    assert llm is not None
    assert isinstance(llm, ChatOpenAI)
    

def test_azure_openai_creation():
    config = AzureOpenAIConfig(
        api_key="azure-key",
        temperature=0.3,
        deployment_name="azure-model",
        api_version="1",
        endpoint="https://test-endpoint.com",
    )
    
    llm_factory = LLMFactory()
    llm = llm_factory.get_llm(config)

    assert llm is not None
    assert isinstance(llm, AzureChatOpenAI)

def test_unknown_builder():
    config = LLMConfig(
        api_key="test-key",
        temperature=0.3
    )
    llm_factory = LLMFactory()
    with pytest.raises(ValueError):  
        llm = llm_factory.get_llm(config)

