import pytest

from flotilla.container.component_compiler import ComponentCompiler
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.core.errors import FlotillaConfigurationError, ReferenceResolutionError


# -----------------------------
# Fake factories for testing
# -----------------------------


def simple_factory(**kwargs):
    return {"type": "simple", "kwargs": kwargs}


def no_arg_factory():
    return {"type": "no_arg"}


def composite_factory(child, value):
    return {"type": "composite", "child": child, "value": value}


def list_factory(items):
    return {"type": "list", "items": items}


def map_factory(mapping):
    return {"type": "map", "mapping": mapping}


# -----------------------------
# Test helpers
# -----------------------------


def create_container(config: dict) -> FlotillaContainer:
    settings = FlotillaSettings(raw=config)
    container = FlotillaContainer(settings=settings)

    container.register_provider("simple", simple_factory)
    container.register_provider("no_arg", no_arg_factory)
    container.register_provider("composite", composite_factory)
    container.register_provider("list_factory", list_factory)
    container.register_provider("map_factory", map_factory)

    return container


def compile_config(config: dict) -> FlotillaContainer:
    container = create_container(config)
    compiler = ComponentCompiler(container=container)

    compiler.discover_components(config)
    compiler.analyze_dependencies()
    compiler.instantiate_components()

    return container


# -----------------------------
# Tests
# -----------------------------


def test_compile_simple_component():
    config = {"a": {"factory": "simple", "x": 1}}
    container = compile_config(config)
    assert container.get("a")["kwargs"]["x"] == 1


def test_ref_name_overrides_path():
    config = {
        "root": {
            "checkpointer": {
                "factory": "no_arg",
                "ref_name": "checkpointer",
            }
        }
    }
    container = compile_config(config)
    assert container.exists("checkpointer")


def test_ref_injection():
    config = {
        "child": {"factory": "no_arg"},
        "parent": {
            "factory": "composite",
            "child": {"$ref": "child"},
            "value": 42,
        },
    }

    container = compile_config(config)
    assert container.get("parent")["child"] is container.get("child")


def test_ref_missing_component_raises():
    config = {
        "a": {
            "factory": "simple",
            "x": {"$ref": "missing"},
        }
    }

    with pytest.raises(ReferenceResolutionError):
        compile_config(config)


def test_list_injection():
    config = {
        "a": {"factory": "no_arg"},
        "b": {"factory": "no_arg"},
        "c": {
            "factory": "list_factory",
            "items": {
                "$list": [
                    {"$ref": "a"},
                    {"$ref": "b"},
                ]
            },
        },
    }

    container = compile_config(config)
    assert len(container.get("c")["items"]) == 2


def test_map_injection():
    config = {
        "a": {"factory": "no_arg"},
        "b": {"factory": "no_arg"},
        "c": {
            "factory": "map_factory",
            "mapping": {
                "$map": {
                    "one": {"$ref": "a"},
                    "two": {"$ref": "b"},
                }
            },
        },
    }

    container = compile_config(config)
    assert container.get("c")["mapping"]["one"] is container.get("a")


def test_raw_list_is_illegal():
    config = {"a": {"factory": "simple", "x": [1, 2]}}
    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_raw_map_is_illegal():
    config = {"a": {"factory": "simple", "x": {"y": 1}}}
    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_component_cycle_detected():
    config = {
        "a": {"factory": "simple", "x": {"$ref": "b"}},
        "b": {"factory": "simple", "x": {"$ref": "a"}},
    }

    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


##################################################


def test_ref_scalar_form_is_invalid():
    config = {
        "a": {"factory": "simple", "dep": "$ref other"},
        "other": {"factory": "simple"},
    }

    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_list_scalar_form_is_invalid():
    config = {"a": {"factory": "simple", "deps": "$list [1,2,3]"}}

    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_map_scalar_form_is_invalid():
    config = {
        "a": {
            "factory": "map_factory",
            "mapping": "$map something",
        }
    }

    with pytest.raises(FlotillaConfigurationError):
        compile_config(config)


def test_nested_component_definition_is_allowed():
    config = {
        "root": {
            "factory": "composite",
            "value": 100,
            "child": {
                "factory": "composite",
                "value": "this is a string",
                "child": {"factory": "no_arg"},
            },
        }
    }

    # Should not raise
    container = compile_config(config)

    assert container is not None


def test_deeply_nested_component_definition_is_allowed():
    config = {
        "root": {
            "factory": "composite",
            "child": {
                "factory": "composite",
                "child": {
                    "factory": "simple",
                    "x": 10,
                },
                "value": 1,
            },
            "value": 2,
        }
    }

    container = compile_config(config)

    root = container.get("root")
    assert root["value"] == 2
    assert root["child"]["value"] == 1
    assert root["child"]["child"]["kwargs"]["x"] == 10
