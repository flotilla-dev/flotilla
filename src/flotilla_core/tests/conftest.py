# tests/conftest.py
import pytest
import yaml
from pathlib import Path
from typing import List, Optional, Callable

from flotilla.tools.flotilla_tool import FlotillaTool

from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.core.flotilla_runtime import FlotillaRuntime


class MockFlotillaRuntime(FlotillaRuntime):
    def run(self, *, agent_input, execution_config, checkpoint=None):
        return super().run(
            agent_input=agent_input,
            execution_config=execution_config,
            checkpoint=checkpoint,
        )

    def stream(self, *, agent_input, execution_config, checkpoint=None):
        return super().stream(
            agent_input=agent_input,
            execution_config=execution_config,
            checkpoint=checkpoint,
        )


@pytest.fixture
def mock_flotilla_runtime_factory():
    def factory(**kwargs):
        return MockFlotillaRuntime()

    return factory


@pytest.fixture
def write_yaml():
    """Helper to write YAML files inside tests."""

    def _write(path: Path, data: dict):
        with open(path, "w") as f:
            yaml.safe_dump(data, f)

    return _write


class MockFlotillaTool(FlotillaTool):
    def __init__(self, name: str, description: str, func: Callable):
        self._name = name
        self._description = description
        self._func = func
        super().__init__()

    @property
    def name(self) -> str:
        return self._name

    @property
    def desciption(self) -> str:
        return self._description

    def execution_callable(self) -> Callable:
        return self._func


@pytest.fixture
def tool_factory():
    def _factory(
        *,
        name: str,
        description: Optional[str] = None,
        func: Optional[Callable] = None,
    ) -> FlotillaTool:
        if func is None:

            def func(**kwargs):
                return "ok"

        return MockFlotillaTool(name=name, description=description, func=func)

    return _factory


@pytest.fixture
def minimal_settings():
    return FlotillaSettings({})
