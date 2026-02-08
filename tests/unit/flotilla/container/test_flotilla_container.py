import pytest

from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.core.errors import FlotillaConfigurationError


@pytest.fixture
def minimal_settings():
    """
    Minimal FlotillaSettings used to verify container initialization.
    No YAML, no env, no wiring assumptions.
    """
    return FlotillaSettings(
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



def test_flotilla_container_initializes_with_settings(flotilla_container, minimal_settings):
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



def test_register_builder_adds_builder(flotilla_container):
    def dummy_builder():
        pass

    flotilla_container.register_factory("test.builder", dummy_builder)

    assert "test.builder" in flotilla_container._factories
    assert flotilla_container._factories["test.builder"] is dummy_builder


