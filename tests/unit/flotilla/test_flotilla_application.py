# tests/unit/flotilla/test_flotilla_application.py

import pytest
from unittest.mock import MagicMock

from flotilla.flotilla_application import FlotillaApplication
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.container.base_contributors import WiringContributor
from flotilla.config.sources.dict_configuration_source import DictConfigurationSource


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------

@pytest.fixture
def empty_sources():
    return [DictConfigurationSource({})]


@pytest.fixture
def no_secrets():
    return []


@pytest.fixture
def app(empty_sources, no_secrets):
    return FlotillaApplication(
        sources=empty_sources,
        secrets=no_secrets,
    )


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


def test_application_registers_default_contributors(app):
    # No explicit assertion on wiring side-effects yet;
    # container build success is the contract.
    app.start()
    assert isinstance(app.container, FlotillaContainer)


def test_application_allows_custom_contributor_registration(empty_sources, no_secrets):
    app = FlotillaApplication(
        sources=empty_sources,
        secrets=no_secrets,
    )

    mock_contributor = MagicMock(spec=WiringContributor)
    mock_contributor.priority = 0

    app.register_contributor(mock_contributor)
    app.start()

    mock_contributor.contribute.assert_called_once()
    mock_contributor.validate.assert_called_once()


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
