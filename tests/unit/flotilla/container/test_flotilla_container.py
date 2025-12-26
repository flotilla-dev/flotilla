import pytest

from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.settings import FlotillaSettings


@pytest.fixture
def minimal_settings():
    """
    Minimal FlotillaSettings used to verify container initialization.
    No YAML, no env, no wiring assumptions.
    """
    return FlotillaSettings.from_dict(
        {
            "core": {
                "agent_selector": {
                    "builder": "agent_selector.keyword"
                }
            }
        }
    )

@pytest.fixture
def flotilla_container(minimal_settings):
    """
    FlotillaContainer constructed with settings instead of config_dir/env.
    """
    return FlotillaContainer(minimal_settings)

@pytest.mark.unit
class TestFlotillaContainer:

    def test_flotilla_container_initializes_with_settings(self, flotilla_container, minimal_settings):
        """
        FlotillaContainer should accept FlotillaSettings and expose them via di.config.
        """

        # container retains the settings reference
        assert flotilla_container.settings is minimal_settings

        # settings are mounted into providers.Configuration
        assert (
            flotilla_container
            .di
            .config
            .core
            .agent_selector
            .builder()
            == "agent_selector.keyword"
        )

    def test_flotilla_container_no_longer_accepts_config_dir_and_env(self):
        """
        Old constructor signature should no longer be supported.
        """
        with pytest.raises(TypeError):
            FlotillaContainer(config_dir="config", env="local")  # type: ignore

