import asyncio
import pytest

from flotilla.container.component_compiler import ComponentCompiler
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.config.errors import FlotillaConfigurationError, ReferenceResolutionError


# -----------------------------
# Fake providers for testing
# -----------------------------


def simple_provider(**kwargs):
    return {"type": "simple", "kwargs": kwargs}


def no_arg_provider():
    return {"type": "no_arg"}


def composite_provider(child, value):
    return {"type": "composite", "child": child, "value": value}


def list_provider(items):
    return {"type": "list", "items": items}


def map_provider(mapping):
    return {"type": "map", "mapping": mapping}


async def async_provider(value):
    return {"type": "async", "value": value}


# -----------------------------
# Test helpers
# -----------------------------


def create_container(config: dict) -> FlotillaContainer:
    settings = FlotillaSettings(raw=config)
    container = FlotillaContainer(settings=settings)

    container.register_provider("simple", simple_provider)
    container.register_provider("no_arg", no_arg_provider)
    container.register_provider("composite", composite_provider)
    container.register_provider("list_provider", list_provider)
    container.register_provider("map_provider", map_provider)
    container.register_provider("async_provider", async_provider)

    return container


def compile_config(config: dict) -> FlotillaContainer:
    container = create_container(config)
    compiler = ComponentCompiler(container=container)

    compiler.discover_components(config)
    compiler.analyze_dependencies()
    asyncio.run(compiler.instantiate_components())

    return container


def get(container: FlotillaContainer, name: str, **kwargs):
    return asyncio.run(container.get(name, **kwargs))


# -----------------------------
# Tests
# -----------------------------


def test_compile_simple_component():
    config = {"a": {"$provider": "simple", "x": 1}}
    container = compile_config(config)
    assert get(container, "a")["kwargs"]["x"] == 1


def test_compile_async_provider_component():
    config = {"a": {"$provider": "async_provider", "value": 1}}
    container = compile_config(config)
    assert get(container, "a") == {"type": "async", "value": 1}


def test_name_override_replaces_path_name():
    config = {
        "services": {
            "user": {
                "$provider": "no_arg",
                "$name": "custom_user",
            }
        }
    }

    container = compile_config(config)

    assert container.exists("custom_user")
    assert not container.exists("services.user")


def test_ref_injection():
    config = {
        "child": {"$provider": "no_arg"},
        "parent": {
            "$provider": "composite",
            "child": {"$ref": "child"},
            "value": 42,
        },
    }

    container = compile_config(config)
    assert get(container, "parent")["child"] is get(container, "child")


def test_ref_missing_component_raises():
    config = {
        "a": {
            "$provider": "simple",
            "x": {"$ref": "missing"},
        }
    }

    with pytest.raises(ReferenceResolutionError):
        compile_config(config)


def test_list_injection():
    config = {
        "a": {"$provider": "no_arg"},
        "b": {"$provider": "no_arg"},
        "c": {
            "$provider": "list_provider",
            "items": {
                "$list": [
                    {"$ref": "a"},
                    {"$ref": "b"},
                ]
            },
        },
    }

    container = compile_config(config)
    assert len(get(container, "c")["items"]) == 2


def test_map_injection():
    config = {
        "a": {"$provider": "no_arg"},
        "b": {"$provider": "no_arg"},
        "c": {
            "$provider": "map_provider",
            "mapping": {
                "$map": {
                    "one": {"$ref": "a"},
                    "two": {"$ref": "b"},
                }
            },
        },
    }

    container = compile_config(config)
    assert get(container, "c")["mapping"]["one"] is get(container, "a")


def test_raw_list_is_illegal():
    config = {"a": {"$provider": "simple", "x": [1, 2]}}
    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_raw_map_is_illegal():
    config = {"a": {"$provider": "simple", "x": {"y": 1}}}
    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_component_cycle_detected():
    config = {
        "a": {"$provider": "simple", "x": {"$ref": "b"}},
        "b": {"$provider": "simple", "x": {"$ref": "a"}},
    }

    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


##################################################


def test_ref_scalar_form_is_invalid():
    config = {
        "a": {"$provider": "simple", "dep": "$ref other"},
        "other": {"$provider": "simple"},
    }

    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_list_scalar_form_is_invalid():
    config = {"a": {"$provider": "simple", "deps": "$list [1,2,3]"}}

    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_map_scalar_form_is_invalid():
    config = {
        "a": {
            "$provider": "map_provider",
            "mapping": "$map something",
        }
    }

    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_nested_component_definition_is_allowed():
    config = {
        "root": {
            "$provider": "composite",
            "value": 100,
            "child": {
                "$provider": "composite",
                "value": "this is a string",
                "child": {"$provider": "no_arg"},
            },
        }
    }

    # Should not raise
    container = compile_config(config)

    assert container is not None


def test_deeply_nested_component_definition_is_allowed():
    config = {
        "root": {
            "$provider": "composite",
            "child": {
                "$provider": "composite",
                "child": {
                    "$provider": "simple",
                    "x": 10,
                },
                "value": 1,
            },
            "value": 2,
        }
    }

    container = compile_config(config)

    root = get(container, "root")
    assert root["value"] == 2
    assert root["child"]["value"] == 1
    assert root["child"]["child"]["kwargs"]["x"] == 10


class TestClass:
    def __init__(self, x):
        self.x = x


def test_class_provider_instantiation():
    config = {
        "a": {
            "$class": "container.test_component_compiler.TestClass",
            "x": 5,
        }
    }
    container = compile_config(config)

    assert get(container, "a").x == 5


def test_default_component_name_from_path():
    config = {"services": {"user": {"$provider": "no_arg"}}}

    container = compile_config(config)

    assert container.exists("services.user")


def test_multiple_provider_directives_invalid():
    config = {
        "a": {
            "$provider": "simple",
            "$class": "something.Class",
        }
    }

    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_embedded_component_in_list():
    config = {
        "a": {
            "$provider": "list_provider",
            "items": {
                "$list": [
                    {"$provider": "no_arg"},
                    {"$provider": "no_arg"},
                ]
            },
        }
    }

    container = compile_config(config)
    assert len(get(container, "a")["items"]) == 2


def test_provider_scalar_form_invalid():
    config = {"a": "$provider simple"}

    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_ref_allowed_as_argument_value():
    config = {
        "other": {"$provider": "no_arg"},
        "root": {
            "$provider": "simple",
            "dep": {"$ref": "other"},
        },
    }

    container = compile_config(config)
    assert get(container, "root")["kwargs"]["dep"] is get(container, "other")


def test_ref_not_allowed_as_sibling_directive_in_component_definition():
    config = {
        "root": {
            "$provider": "simple",
            "$ref": "other",
        }
    }

    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_factory_definition_creates_factory_binding():
    config = {
        "service_factory": {
            "$factory": "simple",
            "x": 1,
        }
    }

    container = compile_config(config)

    first = get(container, "service_factory")
    second = get(container, "service_factory", x=2)

    assert first == {"type": "simple", "kwargs": {"x": 1}}
    assert second == {"type": "simple", "kwargs": {"x": 2}}
    assert first is not second


def test_ref_with_params_invokes_factory_binding():
    config = {
        "child_factory": {
            "$factory": "simple",
            "x": 1,
        },
        "root": {
            "$provider": "composite",
            "child": {
                "$ref": "child_factory",
                "$params": {
                    "x": 9,
                },
            },
            "value": 42,
        },
    }

    container = compile_config(config)

    assert get(container, "root")["child"] == {"type": "simple", "kwargs": {"x": 9}}


def test_ref_with_params_against_singleton_raises():
    config = {
        "child": {"$provider": "simple", "x": 1},
        "root": {
            "$provider": "composite",
            "child": {
                "$ref": "child",
                "$params": {
                    "x": 9,
                },
            },
            "value": 42,
        },
    }

    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_yaml_component_can_reference_preinstalled_binding():
    config = {
        "root": {
            "$provider": "composite",
            "child": {"$ref": "external"},
            "value": 42,
        },
    }

    container = create_container(config)
    external = {"external": True}
    container._install_instance_binding(component_name="external", component=external)
    compiler = ComponentCompiler(container=container)

    compiler.discover_components(config)
    compiler.analyze_dependencies()
    asyncio.run(compiler.instantiate_components())

    assert get(container, "root")["child"] is external
