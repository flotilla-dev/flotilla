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
    return {
        "type": "composite",
        "child": child,
        "value": value,
    }


def list_factory(items):
    return {
        "type": "list",
        "items": items,
    }


def dict_factory(mapping):
    return {
        "type": "dict",
        "mapping": mapping,
    }


# -----------------------------
# Test helpers
# -----------------------------

def create_container(config: dict) -> FlotillaContainer:
    """
    Correct container construction:
    - Settings created from raw config
    - Container initialized with settings
    - factorys registered BEFORE compiler runs
    """
    settings = FlotillaSettings(raw=config)
    container = FlotillaContainer(settings=settings)

    container.register_factory("simple", simple_factory)
    container.register_factory("no_arg", no_arg_factory)
    container.register_factory("composite", composite_factory)
    container.register_factory("list_factory", list_factory)
    container.register_factory("dict_factory", dict_factory)

    return container


def compile_config(config: dict) -> FlotillaContainer:
    """
    Convenience helper mirroring real usage:
    container.build() would normally orchestrate this.
    """
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
    config = {
        "a": {
            "factory": "simple",
            "x": 1,
            "y": "test",
        }
    }

    container = compile_config(config)

    instance = container.get("a")
    assert instance["type"] == "simple"
    assert instance["kwargs"] == {"x": 1, "y": "test"}


def test_ref_name_overrides_path():
    config = {
        "flotilla": {
            "checkpointer": {
                "factory": "no_arg",
                "ref_name": "checkpointer",
            }
        }
    }

    container = compile_config(config)

    assert container.exists("checkpointer")
    assert not container.exists("flotilla.checkpointer")


def test_duplicate_component_names_error():
    config = {
        "a": {
            "factory": "no_arg",
            "ref_name": "dup",
        },
        "b": {
            "factory": "no_arg",
            "ref_name": "dup",
        },
    }

    with pytest.raises(FlotillaConfigurationError, match="already exists"):
        compile_config(config)


def test_ref_injection():
    config = {
        "child": {
            "factory": "no_arg",
        },
        "parent": {
            "factory": "composite",
            "child": {"$ref": "child"},
            "value": 42,
        },
    }

    container = compile_config(config)

    parent = container.get("parent")
    child = container.get("child")

    assert parent["child"] is child
    assert parent["value"] == 42


def test_ref_missing_component_raises():
    config = {
        "a": {
            "factory": "simple",
            "x": {"$ref": "missing"},
        }
    }

    with pytest.raises(ReferenceResolutionError):
        compile_config(config)


def test_embedded_component():
    config = {
        "parent": {
            "factory": "composite",
            "child": {
                "factory": "simple",
                "x": 10,
            },
            "value": 5,
        }
    }

    container = compile_config(config)

    parent = container.get("parent")
    assert parent["child"]["kwargs"]["x"] == 10
    assert parent["value"] == 5


def test_list_injection():
    config = {
        "item1": {"factory": "no_arg"},
        "item2": {"factory": "no_arg"},
        "list_comp": {
            "factory": "list_factory",
            "items": {
                "$list": [
                    {"$ref": "item1"},
                    {"$ref": "item2"},
                ]
            },
        },
    }

    container = compile_config(config)

    result = container.get("list_comp")
    assert len(result["items"]) == 2


def test_dict_injection():
    config = {
        "a": {"factory": "no_arg"},
        "b": {"factory": "no_arg"},
        "dict_comp": {
            "factory": "dict_factory",
            "mapping": {
                "$dict": {
                    "one": {"$ref": "a"},
                    "two": {"$ref": "b"},
                }
            },
        },
    }

    container = compile_config(config)

    result = container.get("dict_comp")
    assert "one" in result["mapping"]
    assert "two" in result["mapping"]


def test_raw_list_is_illegal():
    config = {
        "a": {
            "factory": "simple",
            "x": [1, 2, 3],
        }
    }

    with pytest.raises(FlotillaConfigurationError, match="raw lists"):
        compile_config(config)


def test_raw_dict_is_illegal():
    config = {
        "a": {
            "factory": "simple",
            "x": {"y": 1},
        }
    }

    with pytest.raises(FlotillaConfigurationError, match="raw object"):
        compile_config(config)


def test_component_cycle_detected():
    config = {
        "a": {
            "factory": "simple",
            "x": {"$ref": "b"},
        },
        "b": {
            "factory": "simple",
            "x": {"$ref": "a"},
        },
    }

    with pytest.raises(FlotillaConfigurationError, match="cycle"):
        compile_config(config)
