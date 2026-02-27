import pytest

from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.config.errors import FlotillaConfigurationError, ReferenceResolutionError


@pytest.fixture
def minimal_settings():
    # Keep minimal; build() will be monkeypatched
    return FlotillaSettings({"app": {"name": "test"}})


@pytest.fixture
def container(minimal_settings):
    return FlotillaContainer(minimal_settings)


def test_container_initializes(container, minimal_settings):
    assert container.settings is minimal_settings
    assert container.config_dict == minimal_settings.config


def test_register_provider_and_get_provider_pre_build(container):
    def provider():
        return object()

    assert container.get_provider("p") is None
    container.register_provider("p", provider)
    assert container.get_provider("p") is provider


def test_register_provider_raises_after_build(container):
    container._built = True
    with pytest.raises(RuntimeError):
        container.register_provider("p", lambda: object())


def test_register_component_raises_after_build(container):
    container._built = True
    with pytest.raises(RuntimeError):
        container.register_component(component_name="x", component=object())


def test_register_factory_raises_after_build(container):
    container._built = True
    with pytest.raises(RuntimeError):
        container.register_factory("x", lambda: object())


def test_get_raises_if_missing(container):
    container._built = True
    with pytest.raises(FlotillaConfigurationError):
        container.get("missing")


def test_register_component_and_get_returns_instance(container):
    obj = object()
    container.register_component(component_name="x", component=obj)

    container._built = True
    assert container.get("x") is obj


def test_register_factory_and_get_creates_instance(container):
    calls = {"n": 0}

    def make():
        calls["n"] += 1
        return {"ok": True}

    container.register_factory("x", make)

    container._built = True
    v1 = container.get("x")
    v2 = container.get("x")

    assert v1 == {"ok": True}
    assert v2 == {"ok": True}
    # FactoryBinding semantics: typically new instance each call.
    # If your FactoryBinding caches, adjust this assertion.
    assert calls["n"] == 2


def test_exists_true_false(container, monkeypatch):
    # This test expects exists() to be implemented as: `return name in self._bindings`
    container.register_component(component_name="x", component=object())
    container._built = True

    assert container.exists("x")
    assert not container.exists("missing")


def test_find_instances_by_type_requires_build(container):
    with pytest.raises(RuntimeError):
        container.find_instances_by_type(object)


def test_find_instances_by_type_finds_matches(container):
    class A: ...

    class B: ...

    a = A()
    b = B()

    container.register_component(component_name="a", component=a)
    container.register_component(component_name="b", component=b)

    container._built = True

    matches_a = container.find_instances_by_type(A)
    matches_b = container.find_instances_by_type(B)

    assert matches_a == [a]
    assert matches_b == [b]


def test_find_instances_by_type_skips_unresolvable_bindings(container, monkeypatch):
    # This matches your current behavior (skip resolve() failures).
    class A: ...

    container.register_component(component_name="a", component=A())

    # register a factory that raises
    def bad_factory():
        raise RuntimeError("boom")

    container.register_factory("bad", bad_factory)

    container._built = True

    matches = container.find_instances_by_type(A)
    assert len(matches) == 1
    assert isinstance(matches[0], A)


def test_find_one_by_type_raises_if_none(container):
    class A: ...

    container._built = True
    with pytest.raises(FlotillaConfigurationError):
        container.find_one_by_type(A)


def test_find_one_by_type_raises_if_multiple(container):
    class A: ...

    container.register_component(component_name="a1", component=A())
    container.register_component(component_name="a2", component=A())
    container._built = True

    with pytest.raises(FlotillaConfigurationError):
        container.find_one_by_type(A)


def test_build_sets_built_and_is_one_shot(container, monkeypatch):
    # Stub out compiler so build() doesn't depend on full compilation stack
    class DummyCompiler:
        def __init__(self, container): ...
        def discover_components(self, config): ...
        def analyze_dependencies(self): ...
        def instantiate_components(self): ...

    import flotilla.container.flotilla_container as fc_mod

    monkeypatch.setattr(fc_mod, "ComponentCompiler", DummyCompiler)

    assert container._built is False
    container.build()
    assert container._built is True

    with pytest.raises(RuntimeError):
        container.build()
