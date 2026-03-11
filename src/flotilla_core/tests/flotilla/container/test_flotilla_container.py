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


def test_create_requires_container_built(container):
    class App:
        def __init__(self): ...

    with pytest.raises(RuntimeError):
        container.create(App)


def test_create_injects_single_dependency(container):
    class Service: ...

    class App:
        def __init__(self, service: Service):
            self.service = service

    svc = Service()
    container.register_component(component_name="service", component=svc)

    container._built = True
    app = container.create(App)

    assert isinstance(app, App)
    assert app.service is svc


def test_create_injects_multiple_dependencies(container):
    class A: ...

    class B: ...

    class App:
        def __init__(self, a: A, b: B):
            self.a = a
            self.b = b

    a = A()
    b = B()

    container.register_component(component_name="a", component=a)
    container.register_component(component_name="b", component=b)

    container._built = True
    app = container.create(App)

    assert app.a is a
    assert app.b is b


def test_create_raises_if_dependency_missing(container):
    class Service: ...

    class App:
        def __init__(self, service: Service): ...

    container._built = True

    with pytest.raises(FlotillaConfigurationError):
        container.create(App)


def test_create_raises_if_multiple_dependency_matches(container):
    class Service: ...

    class App:
        def __init__(self, service: Service): ...

    container.register_component(component_name="s1", component=Service())
    container.register_component(component_name="s2", component=Service())

    container._built = True

    with pytest.raises(FlotillaConfigurationError):
        container.create(App)


def test_create_requires_type_annotations(container):
    class Service: ...

    class App:
        def __init__(self, service):
            self.service = service

    container.register_component(component_name="service", component=Service())
    container._built = True

    with pytest.raises(FlotillaConfigurationError):
        container.create(App)


def test_create_uses_default_value_if_dependency_missing(container):
    class App:
        def __init__(self, timeout: int = 30):
            self.timeout = timeout

    container._built = True

    app = container.create(App)

    assert app.timeout == 30


def test_create_prefers_container_dependency_over_default(container):
    class App:
        def __init__(self, value: int = 30):
            self.value = value

    container.register_component(component_name="value", component=99)

    container._built = True
    app = container.create(App)

    assert app.value == 99


def test_create_wraps_constructor_errors(container):
    class Service: ...

    class App:
        def __init__(self, service: Service):
            raise RuntimeError("boom")

    container.register_component(component_name="service", component=Service())
    container._built = True

    with pytest.raises(FlotillaConfigurationError):
        container.create(App)


def test_create_class_with_no_dependencies(container):
    class App:
        def __init__(self):
            self.ok = True

    container._built = True

    app = container.create(App)

    assert isinstance(app, App)
    assert app.ok is True


def test_create_ignores_self_parameter(container):
    class App:
        def __init__(self):
            pass

    container._built = True

    app = container.create(App)
    assert isinstance(app, App)


def test_create_resolves_factory_binding(container):
    class Service: ...

    class App:
        def __init__(self, service: Service):
            self.service = service

    container.register_factory("service", Service)

    container._built = True

    app = container.create(App)

    assert isinstance(app.service, Service)


def test_create_requires_class(container):
    container._built = True

    with pytest.raises(FlotillaConfigurationError):
        container.create(object())
