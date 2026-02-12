import pytest

from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.core.errors import FlotillaConfigurationError
from flotilla.core.flotilla_runtime import FlotillaRuntime
from flotilla.core.runtimes.single_agent_runtime import SingleAgentRuntime
from dependency_injector import providers


@pytest.fixture
def minimal_settings():
    """
    Minimal FlotillaSettings used to verify container initialization.
    No YAML, no env, no wiring assumptions.
    """
    return FlotillaSettings(
        {"core": {"agent_selector": {"builder": "agent_selector.keyword"}}}
    )


@pytest.fixture
def flotilla_container(minimal_settings):
    """
    FlotillaContainer constructed with settings instead of config_dir/env.
    """
    return FlotillaContainer(minimal_settings)


def test_flotilla_container_initializes_with_settings(
    flotilla_container, minimal_settings
):
    """
    FlotillaContainer should accept FlotillaSettings and expose them via di.config.
    """

    # container retains the settings reference
    assert flotilla_container.settings is minimal_settings

    # settings are mounted into providers.Configuration
    assert (
        flotilla_container.di.config.core.agent_selector.builder()
        == "agent_selector.keyword"
    )


def test_register_builder_adds_builder(flotilla_container):
    def dummy_builder():
        pass

    flotilla_container.register_factory("test.builder", dummy_builder)

    assert "test.builder" in flotilla_container._factories
    assert flotilla_container._factories["test.builder"] is dummy_builder


def test_find_instances_by_type_singleton(flotilla_container, agent_factory):
    weather_agent = agent_factory(
        agent_id="weather",
        capabilities=[],
        dependencies=[],
    )
    runtime = SingleAgentRuntime(agent=weather_agent)
    flotilla_container.di.runtime = providers.Object(runtime)
    flotilla_container.build()

    found = flotilla_container.find_one_by_type(FlotillaRuntime)

    assert found is runtime
