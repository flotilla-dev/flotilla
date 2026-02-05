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
    - Builders registered BEFORE compiler runs
    """
    settings = FlotillaSettings(raw=config)
    container = FlotillaContainer(settings=settings)

    container.register_builder("simple", simple_factory)
    container.register_builder("no_arg", no_arg_factory)
    container.register_builder("composite", composite_factory)
    container.register_builder("list_builder", list_factory)
    container.register_builder("dict_builder", dict_factory)

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
            "builder": "simple",
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
                "builder": "no_arg",
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
            "builder": "no_arg",
            "ref_name": "dup",
        },
        "b": {
            "builder": "no_arg",
            "ref_name": "dup",
        },
    }

    with pytest.raises(FlotillaConfigurationError, match="already exists"):
        compile_config(config)


def test_ref_injection():
    config = {
        "child": {
            "builder": "no_arg",
        },
        "parent": {
            "builder": "composite",
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
            "builder": "simple",
            "x": {"$ref": "missing"},
        }
    }

    with pytest.raises(ReferenceResolutionError):
        compile_config(config)


def test_embedded_component():
    config = {
        "parent": {
            "builder": "composite",
            "child": {
                "builder": "simple",
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
        "item1": {"builder": "no_arg"},
        "item2": {"builder": "no_arg"},
        "list_comp": {
            "builder": "list_builder",
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
        "a": {"builder": "no_arg"},
        "b": {"builder": "no_arg"},
        "dict_comp": {
            "builder": "dict_builder",
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
            "builder": "simple",
            "x": [1, 2, 3],
        }
    }

    with pytest.raises(FlotillaConfigurationError, match="raw lists"):
        compile_config(config)


def test_raw_dict_is_illegal():
    config = {
        "a": {
            "builder": "simple",
            "x": {"y": 1},
        }
    }

    with pytest.raises(FlotillaConfigurationError, match="raw object"):
        compile_config(config)


def test_component_cycle_detected():
    config = {
        "a": {
            "builder": "simple",
            "x": {"$ref": "b"},
        },
        "b": {
            "builder": "simple",
            "x": {"$ref": "a"},
        },
    }

    with pytest.raises(FlotillaConfigurationError, match="cycle"):
        compile_config(config)
