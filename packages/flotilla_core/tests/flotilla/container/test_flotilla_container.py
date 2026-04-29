import asyncio
from typing import Annotated, Optional, Union

import pytest

from flotilla.config.errors import FlotillaConfigurationError
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.container.constants import REFLECTION_PROVIDER_KEY
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.container.lifecycle import Shutdown, Startup
from flotilla.container.providers.reflection_provider import ReflectionProvider


@pytest.fixture
def minimal_settings():
    return FlotillaSettings({"app": {"name": "test"}})


@pytest.fixture
def container(minimal_settings):
    return FlotillaContainer(minimal_settings)


def test_container_initializes(container, minimal_settings):
    assert container.settings is minimal_settings
    assert container.config_dict == minimal_settings.config
    assert isinstance(container.get_provider(REFLECTION_PROVIDER_KEY), ReflectionProvider)


def test_register_provider_and_get_provider_pre_build(container):
    def provider():
        return object()

    assert container.get_provider("p") is None
    container.register_provider("p", provider)
    assert container.get_provider("p") is provider


def test_register_provider_raises_if_duplicate(container):
    def provider():
        return object()

    container.register_provider("p", provider)

    with pytest.raises(FlotillaConfigurationError):
        container.register_provider("p", provider)


def test_register_provider_allows_explicit_replace(container):
    def provider_one():
        return "one"

    def provider_two():
        return "two"

    container.register_provider("p", provider_one)
    container.register_provider("p", provider_two, replace=True)

    assert container.get_provider("p") is provider_two


def test_reflection_provider_cannot_be_overwritten_without_replace(container):
    with pytest.raises(FlotillaConfigurationError):
        container.register_provider(REFLECTION_PROVIDER_KEY, ReflectionProvider())


def test_register_provider_raises_after_build(container):
    container._built = True
    with pytest.raises(RuntimeError):
        container.register_provider("p", lambda: object())


def test_private_install_instance_raises_after_build(container):
    container._built = True
    with pytest.raises(RuntimeError):
        container._install_instance_binding(component_name="x", component=object())


def test_private_install_factory_raises_after_build(container):
    container._built = True
    with pytest.raises(RuntimeError):
        container._install_factory_binding("x", lambda: object())


async def test_get_raises_if_missing(container):
    container._built = True
    with pytest.raises(FlotillaConfigurationError):
        await container.get("missing")


async def test_private_install_instance_and_get_returns_instance(container):
    obj = object()
    container._install_instance_binding(component_name="x", component=obj)

    container._built = True
    assert await container.get("x") is obj


async def test_singleton_rejects_get_kwargs(container):
    container._install_instance_binding(component_name="x", component=object())
    container._built = True

    with pytest.raises(FlotillaConfigurationError):
        await container.get("x", value=1)


async def test_private_install_factory_and_get_creates_instances(container):
    calls = {"n": 0}

    def make(value=1):
        calls["n"] += 1
        return {"value": value}

    container._install_factory_binding("x", make, value=2)
    container._built = True

    v1 = await container.get("x")
    v2 = await container.get("x", value=3)

    assert v1 == {"value": 2}
    assert v2 == {"value": 3}
    assert calls["n"] == 2


def test_exists_true_false(container):
    container._install_instance_binding(component_name="x", component=object())
    container._built = True

    assert container.exists("x")
    assert not container.exists("missing")


async def test_find_instances_by_type_requires_build(container):
    with pytest.raises(RuntimeError):
        await container.find_instances_by_type(object)


async def test_find_instances_by_type_finds_matches(container):
    class A: ...

    class B: ...

    a = A()
    b = B()

    container._install_instance_binding(component_name="a", component=a)
    container._install_instance_binding(component_name="b", component=b)
    container._built = True

    assert await container.find_instances_by_type(A) == [a]
    assert await container.find_instances_by_type(B) == [b]


async def test_find_instances_by_type_skips_unresolvable_bindings(container):
    class A: ...

    container._install_instance_binding(component_name="a", component=A())

    def bad_factory():
        raise RuntimeError("boom")

    container._install_factory_binding("bad", bad_factory)
    container._built = True

    matches = await container.find_instances_by_type(A)
    assert len(matches) == 1
    assert isinstance(matches[0], A)


async def test_find_one_by_type_raises_if_none(container):
    class A: ...

    container._built = True
    with pytest.raises(FlotillaConfigurationError):
        await container.find_one_by_type(A)


async def test_find_one_by_type_raises_if_multiple(container):
    class A: ...

    container._install_instance_binding(component_name="a1", component=A())
    container._install_instance_binding(component_name="a2", component=A())
    container._built = True

    with pytest.raises(FlotillaConfigurationError):
        await container.find_one_by_type(A)


def test_build_sets_built_and_is_one_shot(container, monkeypatch):
    class DummyCompiler:
        def __init__(self, container): ...
        def discover_components(self, config): ...
        def register_component_definition(self, node): ...
        def analyze_dependencies(self): ...
        async def instantiate_components(self): ...

    import flotilla.container.flotilla_container as fc_mod

    monkeypatch.setattr(fc_mod, "ComponentCompiler", DummyCompiler)

    assert container._built is False
    asyncio.run(container.build())
    assert container._built is True

    with pytest.raises(RuntimeError):
        asyncio.run(container.build())


async def test_create_requires_container_built(container):
    class App:
        def __init__(self): ...

    with pytest.raises(RuntimeError):
        await container.create_component(App)


async def test_create_injects_single_dependency(container):
    class Service: ...

    class App:
        def __init__(self, service: Service):
            self.service = service

    svc = Service()
    container._install_instance_binding(component_name="service", component=svc)
    container._built = True

    app = await container.create_component(App)

    assert isinstance(app, App)
    assert app.service is svc


async def test_create_resolves_factory_binding(container):
    class Service: ...

    class App:
        def __init__(self, service: Service):
            self.service = service

    container._install_factory_binding("service", Service)
    container._built = True

    app = await container.create_component(App)

    assert isinstance(app.service, Service)


async def test_create_raises_if_dependency_missing(container):
    class Service: ...

    class App:
        def __init__(self, service: Service): ...

    container._built = True

    with pytest.raises(FlotillaConfigurationError):
        await container.create_component(App)


async def test_create_raises_if_multiple_dependency_matches(container):
    class Service: ...

    class App:
        def __init__(self, service: Service): ...

    container._install_instance_binding(component_name="s1", component=Service())
    container._install_instance_binding(component_name="s2", component=Service())
    container._built = True

    with pytest.raises(FlotillaConfigurationError):
        await container.create_component(App)


async def test_create_requires_type_annotations(container):
    class Service: ...

    class App:
        def __init__(self, service):
            self.service = service

    container._install_instance_binding(component_name="service", component=Service())
    container._built = True

    with pytest.raises(FlotillaConfigurationError):
        await container.create_component(App)


async def test_create_uses_default_value_if_dependency_missing(container):
    class App:
        def __init__(self, timeout: int = 30):
            self.timeout = timeout

    container._built = True
    app = await container.create_component(App)

    assert app.timeout == 30


async def test_create_prefers_container_dependency_over_default(container):
    class App:
        def __init__(self, value: int = 30):
            self.value = value

    container._install_instance_binding(component_name="value", component=99)
    container._built = True

    app = await container.create_component(App)

    assert app.value == 99


async def test_create_wraps_constructor_errors(container):
    class Service: ...

    class App:
        def __init__(self, service: Service):
            raise RuntimeError("boom")

    container._install_instance_binding(component_name="service", component=Service())
    container._built = True

    with pytest.raises(FlotillaConfigurationError):
        await container.create_component(App)


async def test_create_class_with_no_dependencies(container):
    class App:
        def __init__(self):
            self.ok = True

    container._built = True
    app = await container.create_component(App)

    assert isinstance(app, App)
    assert app.ok is True


async def test_create_requires_class(container):
    container._built = True

    with pytest.raises(FlotillaConfigurationError):
        await container.create_component(object())


async def test_find_instances_optional_type(container):
    class TelemetryPolicy: ...

    policy = TelemetryPolicy()
    container._install_instance_binding(component_name="telemetry", component=policy)
    container._built = True

    assert await container.find_instances_by_type(Optional[TelemetryPolicy]) == [policy]


async def test_find_instances_union_type(container):
    class TelemetryPolicy: ...

    policy = TelemetryPolicy()
    container._install_instance_binding(component_name="telemetry", component=policy)
    container._built = True

    assert await container.find_instances_by_type(Union[TelemetryPolicy, None]) == [policy]


async def test_find_instances_annotated_type(container):
    class TelemetryPolicy: ...

    policy = TelemetryPolicy()
    container._install_instance_binding(component_name="telemetry", component=policy)
    container._built = True

    assert await container.find_instances_by_type(Annotated[TelemetryPolicy, "meta"]) == [policy]


async def test_find_instances_union_multiple_types(container):
    class A: ...
    class B: ...

    a = A()
    b = B()
    container._install_instance_binding(component_name="a", component=a)
    container._install_instance_binding(component_name="b", component=b)
    container._built = True

    matches = await container.find_instances_by_type(Union[A, B])

    assert set(matches) == {a, b}


async def test_container_startup_and_shutdown_call_component_lifecycle(container):
    events = []

    class Service(Startup, Shutdown):
        async def startup(self):
            events.append("startup")

        async def shutdown(self):
            events.append("shutdown")

    container._install_instance_binding(component_name="service", component=Service())
    container._built = True

    await container.startup(timeout=1)
    await container.shutdown(timeout=1)

    assert events == ["startup", "shutdown"]


async def test_startup_protocol_does_not_require_shutdown(container):
    events = []

    class Service(Startup):
        async def startup(self):
            events.append("startup")

    container._install_instance_binding(component_name="service", component=Service())
    container._built = True

    await container.startup(timeout=1)
    await container.shutdown(timeout=1)

    assert events == ["startup"]


async def test_shutdown_protocol_does_not_require_startup(container):
    events = []

    class Service(Shutdown):
        async def shutdown(self):
            events.append("shutdown")

    container._install_instance_binding(component_name="service", component=Service())
    container._built = True

    await container.startup(timeout=1)
    await container.shutdown(timeout=1)

    assert events == ["shutdown"]


async def test_define_component_is_compiled_during_build(container):
    def provider(value):
        return {"value": value}

    container.register_provider("provider", provider)
    container.define_component("component", provider="provider", value=7)

    await container.build()

    assert await container.get("component") == {"value": 7}


async def test_define_factory_is_compiled_during_build(container):
    def provider(value=1):
        return {"value": value}

    container.register_provider("provider", provider)
    container.define_factory("factory", factory="provider", value=2)

    await container.build()

    assert await container.get("factory") == {"value": 2}
    assert await container.get("factory", value=3) == {"value": 3}


async def test_factory_starts_instances_created_after_container_startup(container):
    events = []

    class Service(Startup, Shutdown):
        async def startup(self):
            events.append("startup")

        async def shutdown(self):
            events.append("shutdown")

    container._install_factory_binding("service", Service)
    container._built = True

    await container.startup(timeout=1)
    instance = await container.get("service")
    await container.shutdown(timeout=1)

    assert isinstance(instance, Service)
    assert events == ["startup", "shutdown"]
