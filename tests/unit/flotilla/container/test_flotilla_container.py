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

def test_flotilla_container_no_longer_accepts_config_dir_and_env():
    """
    Old constructor signature should no longer be supported.
    """
    with pytest.raises(TypeError):
        FlotillaContainer(config_dir="config", env="local")  # type: ignore


def test_register_builder_adds_builder(flotilla_container):
    def dummy_builder():
        pass

    flotilla_container.register_builder("test.builder", dummy_builder)

    assert "test.builder" in flotilla_container._builders
    assert flotilla_container._builders["test.builder"] is dummy_builder


def test_register_contributor_adds_contributor(flotilla_container):
    class DummyContributor:
        priority = 0
        def contribute(self, container): pass
        def validate(self, container): pass

    contributor = DummyContributor()

    flotilla_container.register_contributor(contributor)

    assert contributor in flotilla_container._contributors


def test_build_executes_contributors_in_priority_order(flotilla_container):
    call_order = []

    class ContributorA:
        priority = 10
        def contribute(self, container):
            call_order.append("A")
        def validate(self, container):
            call_order.append("A_validate")

    class ContributorB:
        priority = 5
        def contribute(self, container):
            call_order.append("B")
        def validate(self, container):
            call_order.append("B_validate")

    flotilla_container.register_contributor(ContributorA())
    flotilla_container.register_contributor(ContributorB())

    flotilla_container.build()

    assert call_order == [
        "B", "A",
        "B_validate", "A_validate",
    ]

def test_register_singleton_registers_provider(flotilla_container):
    def dummy_builder():
        return "value"

    flotilla_container.register_singleton("test_singleton", dummy_builder)

    assert hasattr(flotilla_container.di, "test_singleton")
    assert flotilla_container.di.test_singleton() == "value"

def test_register_component_provider_registers_factory(flotilla_container):
    def dummy_builder(name, config, container):
        return f"{name}-built"

    # Simulate config section
    flotilla_container.di.config.from_dict(
        {
            "tools": {
                "tool_a": {"type": "dummy"}
            }
        }
    )

    flotilla_container.register_component_provider(
        section="tools",
        name="tool_a",
        builder=dummy_builder,
    )

    assert hasattr(flotilla_container.di, "tool_a")
    assert flotilla_container.di.tool_a() == "tool_a-built"


def test_register_section_singleton_happy_path(flotilla_container):
    def dummy_builder(container, config):
        return config["value"]

    flotilla_container.register_builder("dummy", dummy_builder)

    flotilla_container.di.config.from_dict(
        {
            "core": {
                "thing": {
                    "builder": "dummy",
                    "value": 42,
                }
            }
        }
    )

    flotilla_container.register_section_singleton(
        section="core",
        name="thing",
        config_path="thing",
    )

    assert flotilla_container.di.thing() == 42


def test_register_section_singleton_raises_if_builder_missing(flotilla_container):
    flotilla_container.di.config.from_dict(
        {
            "core": {
                "thing": {
                    "builder": "missing",
                }
            }
        }
    )

    with pytest.raises(ValueError, match="No builder registered"):
        flotilla_container.register_section_singleton(
            section="core",
            name="thing",
            config_path="thing",
        )


