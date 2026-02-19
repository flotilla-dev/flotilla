# tests/unit/flotilla/test_flotilla_application.py

import pytest
from unittest.mock import MagicMock

from flotilla.flotilla_application import FlotillaApplication
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.sources.dict_configuration_source import DictConfigurationSource


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
def app(min_source, no_secrets, mock_flotilla_runtime_factory):
    app = FlotillaApplication(
        sources=min_source,
        secrets=no_secrets,
    )
    app.register_provider("runtime.mock", mock_flotilla_runtime_factory)

    return app


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


def test_application_initial_state(app):
    assert app.started is False

    with pytest.raises(RuntimeError, match="Application not started"):
        _ = app.container


def test_application_start_builds_container(app):
    app.start()

    assert app.started is True
    assert isinstance(app.container, FlotillaContainer)


def test_container_property_raises_before_start(app):
    with pytest.raises(RuntimeError, match="Application not started"):
        _ = app.container


def test_started_flag_lifecycle(app):
    assert app.started is False

    app.start()
    assert app.started is True

    app.shutdown()
    assert app.started is False


def test_shutdown_clears_container(app):
    app.start()
    assert app.container is not None

    app.shutdown()

    with pytest.raises(RuntimeError):
        _ = app.container
