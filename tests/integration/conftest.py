# tests/conftest.py
import pytest
import yaml
from pathlib import Path
from typing import List, Optional, Callable, Any, Dict
from pydantic import ConfigDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from flotilla.runtime.flotilla_runtime import FlotillaRuntime
from flotilla.tools.flotilla_tool import FlotillaTool


class MockFlotillaRuntime(FlotillaRuntime):
    def __init__(self, **kwargs):
        self.extra_kwargs = kwargs

    def run(self, *, agent_input, execution_config, checkpoint=None):
        pass

    def stream(self, *, agent_input, execution_config, checkpoint=None):
        pass


class MockFlotillaTool(FlotillaTool):
    def __init__(self, name: str, description: str, func: Callable, **kwargs):
        self._name = name
        self._description = description
        self._func = func
        self.extra_kwargs = kwargs
        super().__init__()

    @property
    def name(self) -> str:
        return self._name

    @property
    def llm_description(self) -> str:
        return self._description

    def execution_callable(self) -> Callable:
        return self._func


@pytest.fixture
def mock_flotilla_runtime_factory():
    def factory(**kwargs):
        return MockFlotillaRuntime(**kwargs)

    return factory


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


class MockChatModel(BaseChatModel):
    """Minimal mock LLM for testing"""

    model_config = ConfigDict(extra="allow")

    response: str = "mock response"

    # Dedicated field to store test kwargs
    test_kwargs: Dict[str, Any] = {}

    def __init__(self, **data):
        # Capture extra fields BEFORE Pydantic strips them
        extra = {k: v for k, v in data.items() if k not in self.model_fields}

        super().__init__(**data)

        # Store extras in our test field
        object.__setattr__(self, "test_kwargs", extra)

    def _generate(self, messages, stop=None, **kwargs):
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=self.response))]
        )

    @property
    def _llm_type(self) -> str:
        return "mock-chat-model"


@pytest.fixture
def llm_factory() -> MockChatModel:
    def _factory(**kwargs):
        return MockChatModel(**kwargs)

    return _factory


@pytest.fixture
def mock_llm() -> BaseChatModel:
    """
    Fixture providing a mock BaseChatModel-compatible LLM.
    """
    return MockChatModel()


@pytest.fixture
def agent_factory():
    def _factory(
        *,
        agent_id: str,
        llm: BaseChatModel,
        **kwargs,
    ):
        pass

    return _factory


@pytest.fixture
def tool_factory():
    def _factory(
        *,
        name: str,
        description: Optional[str] = None,
        func: Optional[Callable] = None,
        **kwargs,
    ) -> FlotillaTool:
        if func is None:

            def func(**kwargs):
                return "ok"

        return MockFlotillaTool(name=name, description=description, func=func, **kwargs)

    return _factory
