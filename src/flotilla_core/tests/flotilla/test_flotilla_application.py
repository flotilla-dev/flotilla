# tests/unit/flotilla/test_flotilla_application.py

import pytest
from unittest.mock import MagicMock

from flotilla.flotilla_application import FlotillaApplication
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.sources.dict_configuration_source import DictConfigurationSource
from flotilla.thread.thread_service import ThreadService

# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def min_source():
    return [DictConfigurationSource({"runtime": {"factory": "runtime.mock"}})]


@pytest.fixture
def no_secrets():
    return []


@pytest.fixture
def thread_service(store) -> ThreadService:
    return ThreadService(store=store)


@pytest.fixture
def app(runtime_factory, thread_service, container_factory):
    runtime = runtime_factory()
    app = FlotillaApplication(runtime=runtime, thread_service=thread_service)
    app._attach_container(container=container_factory())
    return app


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


def test_application_initial_state(app):
    assert app.started is False

    with pytest.raises(RuntimeError, match="Application not started"):
        _ = app.runtime


def test_application_start_builds_container(app):
    app.start()

    assert app.started is True
    assert isinstance(app._container, FlotillaContainer)


def test_runtime_property_raises_before_start(app):
    with pytest.raises(RuntimeError, match="Application not started"):
        _ = app.runtime


def test_started_flag_lifecycle(app):
    assert app.started is False

    app.start()
    assert app.started is True

    app.shutdown()
    assert app.started is False


def test_shutdown_clears_raises_on_runtime(app):
    app.start()
    assert app._container is not None

    app.shutdown()

    with pytest.raises(RuntimeError):
        _ = app.runtime
