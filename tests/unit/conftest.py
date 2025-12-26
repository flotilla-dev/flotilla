# tests/conftest.py
import pytest
import yaml
from pathlib import Path
from typing import List
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from flotilla.agents.base_business_agent import BaseBusinessAgent, AgentCapability, ToolDependency
from flotilla.tools.tool_registry import ToolRegistry
from flotilla.agents.agent_selector import AgentSelector
from flotilla.agents.selectors.keyword_agent_selector import KeywordAgentSelector


class MockBusinessAgent(BaseBusinessAgent):
    def __init__(self, *, agent_id, agent_name, llm, checkpointer, capabilities:List[AgentCapability], dependencies:List[ToolDependency]):
        self.capabilities = capabilities
        self.tool_dependencies = dependencies
        super().__init__(agent_id=agent_id, agent_name=agent_name, llm=llm, checkpointer=checkpointer)


    def _initialize_capabilities(self):
        return self.capabilities
    
    def _initialize_dependencies(self):
        return self.tool_dependencies


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Creates a temporary config directory with empty default files."""
    for name in ["flotilla", "agents", "tools", "feature_flags"]:
        (tmp_path / f"{name}.yml").write_text("{}")
    return tmp_path


@pytest.fixture
def write_yaml():
    """Helper to write YAML files inside tests."""
    def _write(path: Path, data: dict):
        with open(path, "w") as f:
            yaml.safe_dump(data, f)
    return _write


@pytest.fixture
def mock_checkpointer():
    return InMemorySaver

class MockChatModel(BaseChatModel):
    """Minimal mock LLM for testing"""

    response: str = "mock response"   # ← pydantic field

    def _generate(self, messages, stop=None, **kwargs):
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(content=self.response)
                )
            ]
        )

    @property
    def _llm_type(self) -> str:
        return "mock-chat-model"


@pytest.fixture
def mock_llm() -> BaseChatModel:
    """
    Fixture providing a mock BaseChatModel-compatible LLM.
    """
    return MockChatModel()

@pytest.fixture
def mock_tool_registry() -> ToolRegistry:
    return ToolRegistry(tool_providers=[])

@pytest.fixture
def mock_agent_selector() -> AgentSelector:
    return KeywordAgentSelector(min_confidence=0.2)

@pytest.fixture
def agent_factory(mock_llm, mock_checkpointer):
    def _factory(*, agent_id:str, capabilities: List[AgentCapability] | None, dependencies: List[ToolDependency] | None):
        return MockBusinessAgent(
            agent_id=agent_id,
            agent_name=agent_id,
            llm=mock_llm,
            checkpointer=mock_checkpointer,
            capabilities=capabilities,
            dependencies=dependencies
        )
    return _factory
