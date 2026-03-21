import pytest

from flotilla.container.providers.reflection_provider import ReflectionProvider
from flotilla.config.errors import FlotillaConfigurationError


# ---------------------------------
# Test helper classes
# ---------------------------------


class SimpleClass:
    def __init__(self):
        self.value = "ok"


class KwargClass:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class FailingConstructor:
    def __init__(self):
        raise RuntimeError("constructor failure")


# ---------------------------------
# Tests
# ---------------------------------


def test_constructs_class_without_args():
    provider = ReflectionProvider()

    obj = provider("container.providers.test_reflection_provider.SimpleClass")

    assert isinstance(obj, SimpleClass)
    assert obj.value == "ok"


def test_constructs_class_with_kwargs():
    provider = ReflectionProvider()

    obj = provider(
        "container.providers.test_reflection_provider.KwargClass",
        x=1,
        y=2,
    )

    assert isinstance(obj, KwargClass)
    assert obj.x == 1
    assert obj.y == 2


def test_invalid_class_path_raises_configuration_error():
    provider = ReflectionProvider()

    with pytest.raises(FlotillaConfigurationError):
        provider("InvalidClassNameWithoutModule")


def test_missing_class_in_module_raises_configuration_error():
    provider = ReflectionProvider()

    with pytest.raises(FlotillaConfigurationError):
        provider("math.NotARealClass")


def test_missing_module_raises_import_error():
    provider = ReflectionProvider()

    with pytest.raises(ModuleNotFoundError):
        provider("not_a_real_module.SomeClass")


def test_constructor_exception_propagates():
    provider = ReflectionProvider()

    with pytest.raises(RuntimeError):
        provider("container.providers.test_reflection_provider.FailingConstructor")
