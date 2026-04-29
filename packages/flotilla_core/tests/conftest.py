# tests/conftest.py
import pytest
import yaml
from pathlib import Path
from typing import List, Optional, Callable, Any, Dict
from unittest.mock import Mock

from flotilla.tools.flotilla_tool import FlotillaTool
from flotilla.thread.thread_entry_store import ThreadEntryStore
from flotilla.thread.in_memory_store import InMemoryStore
from flotilla.telemetry.telemetry_policy import TelemetryPolicy
from flotilla.agents.flotilla_agent import FlotillaAgent
from flotilla.config.secret_resolver import SecretResolver
from flotilla.container.flotilla_container import FlotillaContainer

from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.runtime.flotilla_runtime import FlotillaRuntime
from .runtime_fakes import (
    FaultInjectingStore,
    SpyPhaseContextService,
    SpyExecutionTimeoutPolicy,
    SpySuspendPolicy,
    SpyResumeService,
    FakeOrchestrationStrategy,
    SpyTelemetryPolicy,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def container_factory():
    def _factory(components: Optional[Dict[str, Any]] = {}):
        container = FlotillaContainer(settings=FlotillaSettings({}))
        for name, componet in components.items():
            container._install_instance_binding(component_name=name, component=componet)
        return container

    return _factory


@pytest.fixture
async def store() -> ThreadEntryStore:
    return FaultInjectingStore(inner=InMemoryStore())


@pytest.fixture
def phase_context_service() -> SpyPhaseContextService:
    return SpyPhaseContextService()


@pytest.fixture
def timeout_policy_not_expired() -> SpyExecutionTimeoutPolicy:
    return SpyExecutionTimeoutPolicy(expired=False)


@pytest.fixture
def timeout_policy_expired() -> SpyExecutionTimeoutPolicy:
    return SpyExecutionTimeoutPolicy(expired=True)


@pytest.fixture
def resume_service_valid() -> SpyResumeService:
    return SpyResumeService()


@pytest.fixture
def resume_service_unauthorized() -> SpyResumeService:
    return SpyResumeService(unauthorized=True)


@pytest.fixture
def resume_service_invalid() -> SpyResumeService:
    return SpyResumeService(invalid=True)


@pytest.fixture
def resume_service_expired() -> SpyResumeService:
    return SpyResumeService(expired=True)


@pytest.fixture
def suspend_policy_ok() -> SpySuspendPolicy:
    return SpySuspendPolicy(should_raise=False)


@pytest.fixture
def suspend_policy_failing() -> SpySuspendPolicy:
    return SpySuspendPolicy(should_raise=True)


@pytest.fixture
def strategy() -> FakeOrchestrationStrategy:
    return FakeOrchestrationStrategy()


@pytest.fixture
def telemetry_policy() -> TelemetryPolicy:
    return SpyTelemetryPolicy()


@pytest.fixture
def runtime_factory() -> Callable[..., Any]:
    """
    Replace this with construction of your real FlotillaRuntime.
    The tests assume a Runtime with:
      - run(request: RuntimeRequest) -> RuntimeResponse (sync)
      - or equivalent API your project uses
    """

    def _make_runtime(
        *,
        store: Optional[ThreadEntryStore] = None,
        phase_context_service: Optional[SpyPhaseContextService] = None,
        orchestration_strategy: Optional[FakeOrchestrationStrategy] = None,
        execution_timeout_policy: Optional[SpyExecutionTimeoutPolicy] = None,
        resume_service: Optional[SpyResumeService] = None,
        suspend_policy: Optional[SpySuspendPolicy] = None,
        telemetry_policy: Optional[TelemetryPolicy] = None,
    ):

        store = store or InMemoryStore()
        phase_context_service = phase_context_service or SpyPhaseContextService()
        orchestration_strategy = orchestration_strategy or FakeOrchestrationStrategy()
        execution_timeout_policy = execution_timeout_policy or SpyExecutionTimeoutPolicy(expired=False)
        resume_service = resume_service or SpyResumeService()
        suspend_policy = suspend_policy or SpySuspendPolicy()
        telemetry_policy = telemetry_policy or SpyTelemetryPolicy()

        return FlotillaRuntime(
            orchestration=orchestration_strategy,
            store=store,
            phase_context_service=phase_context_service,
            execution_timeout_policy=execution_timeout_policy,
            resume_service=resume_service,
            suspend_policy=suspend_policy,
            telemetry_policy=telemetry_policy,
        )

    return _make_runtime


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
    def llm_description(self) -> str:
        return self._description

    def execution_callable(self) -> Callable:
        return self._func


class MockFlotillaAgent(FlotillaAgent):
    def __init__(self, *, agent_name, **kwargs):
        self.extra_kwargs = kwargs
        super().__init__(agent_name=agent_name)

    def run(self, thread, phase_context, input_parts=None):
        pass

    def _execute(self, thread, phase_context, input_parts=None):
        return super()._execute(thread, phase_context, input_parts)


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
def agent_factory():
    def _factory(*, name: str, **kwargs) -> FlotillaAgent:
        return MockFlotillaAgent(agent_name=name, **kwargs)

    return _factory


@pytest.fixture
def minimal_settings():
    return FlotillaSettings({})
