# tests/unit/flotilla/test_flotilla_application.py
import pytest
from unittest.mock import MagicMock, patch
from flotilla.flotilla_application import FlotillaApplication
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.container.contributors.base_contributors import WiringContributor



class TestFlotillaApplication:
    def test_application_initial_state(self, minimal_settings):
        app = FlotillaApplication(minimal_settings)

        assert app.settings is minimal_settings
        assert app.started is False

    def test_application_registers_default_builders(self, minimal_settings):
        app = FlotillaApplication(minimal_settings)

        app.start()
        container = app.container

        assert isinstance(container, FlotillaContainer)

    def test_application_registers_default_contributors(self, minimal_settings):
        app = FlotillaApplication(minimal_settings)

        app.start()
        container = app.container

        # We don’t assert specific wiring outcomes yet,
        # only that the container was successfully built
        assert isinstance(container, FlotillaContainer)

    def test_application_allows_custom_contributor_registration(self, minimal_settings):
        app = FlotillaApplication(minimal_settings)

        mock_contributor = MagicMock(spec=WiringContributor)
        mock_contributor.priority = 0

        app.register_contributor(mock_contributor)

        app.start()

        mock_contributor.contribute.assert_called_once()
        mock_contributor.validate.assert_called_once()

    def test_container_property_raises_before_start(minimal_settings):
        app = FlotillaApplication(minimal_settings)

        with pytest.raises(RuntimeError, match="Application not started"):
            _ = app.container


    def test_started_flag_lifecycle(minimal_settings):
        app = FlotillaApplication(minimal_settings)

        assert app.started is False

        app.start()
        assert app.started is True

        app.shutdown()
        assert app.started is False


    def test_shutdown_clears_container(minimal_settings):
        app = FlotillaApplication(minimal_settings)

        app.start()
        assert app.container is not None

        app.shutdown()

        with pytest.raises(RuntimeError):
            _ = app.container
