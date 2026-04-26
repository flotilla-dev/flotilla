import asyncio
import pytest
from unittest.mock import MagicMock

from flotilla.flotilla_application import FlotillaApplication
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.errors import FlotillaConfigurationError


# ------------------------------------------------------------
# Test Services
# ------------------------------------------------------------


class ServiceA:
    pass


class ServiceB:
    pass


class ServiceC:
    pass


# ------------------------------------------------------------
# Test Applications
# ------------------------------------------------------------


class BaseApp(FlotillaApplication):
    service_a: ServiceA


class ChildApp(BaseApp):
    service_b: ServiceB


class OverrideApp(BaseApp):
    service_a: ServiceB


# ------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------


@pytest.fixture
def container():
    container = MagicMock(spec=FlotillaContainer)

    container.find_one_by_type.side_effect = lambda t: {
        ServiceA: ServiceA(),
        ServiceB: ServiceB(),
        ServiceC: ServiceC(),
    }[t]

    return container


# ------------------------------------------------------------
# Lifecycle Tests
# ------------------------------------------------------------


def test_application_initial_state():
    app = FlotillaApplication()

    assert app.started is False


def test_start_sets_started_flag(container):
    app = FlotillaApplication()
    app._attach_container(container)

    asyncio.run(app.build())
    app.start()

    assert app.started is True


def test_shutdown_resets_started_flag(container):
    app = FlotillaApplication()
    app._attach_container(container)

    asyncio.run(app.build())
    app.start()
    app.shutdown()

    assert app.started is False


def test_shutdown_safe_when_not_started():
    app = FlotillaApplication()

    app.shutdown()

    assert app.started is False


# ------------------------------------------------------------
# Container Attachment
# ------------------------------------------------------------


def test_attach_container():
    app = FlotillaApplication()
    container = MagicMock(spec=FlotillaContainer)

    app._attach_container(container)

    assert app._container is container


def test_attach_container_twice_raises():
    app = FlotillaApplication()
    container = MagicMock(spec=FlotillaContainer)

    app._attach_container(container)

    with pytest.raises(FlotillaConfigurationError, match="Container already attached"):
        app._attach_container(container)


# ------------------------------------------------------------
# Build() Resolution
# ------------------------------------------------------------


def test_build_resolves_declared_services(container):
    app = BaseApp()
    app._attach_container(container)
    asyncio.run(app.build())

    assert isinstance(app.service_a, ServiceA)


def test_build_calls_container_lookup(container):
    app = BaseApp()
    app._attach_container(container)

    asyncio.run(app.build())

    container.find_one_by_type.assert_called_with(ServiceA)


def test_build_requires_container():
    app = BaseApp()

    with pytest.raises(RuntimeError):
        asyncio.run(app.build())


def test_build_runs_once(container):
    app = BaseApp()
    app._attach_container(container)

    asyncio.run(app.build())

    with pytest.raises(RuntimeError):
        asyncio.run(app.build())


# ------------------------------------------------------------
# Property Access
# ------------------------------------------------------------


def test_service_property_access(container):
    app = BaseApp()
    app._attach_container(container)

    asyncio.run(app.build())

    assert isinstance(app.service_a, ServiceA)


def test_service_property_is_read_only(container):
    app = BaseApp()
    app._attach_container(container)

    asyncio.run(app.build())

    with pytest.raises(AttributeError):
        app.service_a = ServiceA()


# ------------------------------------------------------------
# MRO Annotation Discovery
# ------------------------------------------------------------


def test_build_resolves_services_from_parent_class(container):
    app = ChildApp()
    app._attach_container(container)

    asyncio.run(app.build())

    assert isinstance(app._service_a, ServiceA)
    assert isinstance(app._service_b, ServiceB)


def test_property_access_from_parent_class(container):
    app = ChildApp()
    app._attach_container(container)

    asyncio.run(app.build())

    assert isinstance(app.service_a, ServiceA)
    assert isinstance(app.service_b, ServiceB)


# ------------------------------------------------------------
# Subclass Override
# ------------------------------------------------------------


def test_subclass_annotation_override(container):
    app = OverrideApp()
    app._attach_container(container)

    asyncio.run(app.build())

    assert isinstance(app._service_a, ServiceB)
    assert isinstance(app.service_a, ServiceB)


# ------------------------------------------------------------
# Annotation Collection
# ------------------------------------------------------------


def test_collect_annotations_empty():
    app = FlotillaApplication()
    annotations = app._collect_annotations()

    assert isinstance(annotations, dict)


# ------------------------------------------------------------
# Forward Reference Resolution
# ------------------------------------------------------------


class ForwardRefApp(FlotillaApplication):
    service_a: "ServiceA"


def test_collect_annotations_resolves_forward_refs():
    app = ForwardRefApp()
    annotations = app._collect_annotations()

    assert annotations["service_a"] is ServiceA


# ------------------------------------------------------------
# Deep MRO Merge
# ------------------------------------------------------------


class GrandParentApp(FlotillaApplication):
    service_a: ServiceA


class ParentApp(GrandParentApp):
    service_b: ServiceB


class ChildAppDeep(ParentApp):
    service_c: ServiceC


def test_collect_annotations_deep_mro_merge():
    app = ChildAppDeep()
    annotations = app._collect_annotations()

    assert annotations["service_a"] is ServiceA
    assert annotations["service_b"] is ServiceB
    assert annotations["service_c"] is ServiceC


# ------------------------------------------------------------
# Subclass Override Priority
# ------------------------------------------------------------


class ParentOverrideApp(FlotillaApplication):
    service_a: ServiceA


class ChildOverrideApp(ParentOverrideApp):
    service_a: ServiceB


def test_collect_annotations_subclass_override_priority():
    app = ChildOverrideApp()
    annotations = app._collect_annotations()

    assert annotations["service_a"] is ServiceB
