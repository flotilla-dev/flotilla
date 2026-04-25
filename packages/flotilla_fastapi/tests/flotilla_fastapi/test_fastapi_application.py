import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla_fastapi.application import FastApiFlotillaApplication
from flotilla_fastapi.config import FastAPIRunConfig
from flotilla_fastapi.handler import HTTPHandler
from flotilla_fastapi.routes import routes


class TestFastAPIFlotillaApplication(FastApiFlotillaApplication):
    def __init__(self):
        super().__init__()
        self.shutdown_called = False
        self.shutdown_count = 0

    def _execute_shutdown(self) -> None:
        self.shutdown_called = True
        self.shutdown_count += 1


def build_container(*components):
    container = FlotillaContainer(FlotillaSettings(raw={}))

    for i, component in enumerate(components):
        container.register_component(component_name=f"component_{i}", component=component)

    container.build()
    return container


def test_build_resolves_fastapi_adapter():
    container = build_container()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    application.build()

    assert application.adapter is not None


def test_app_property_exposes_fastapi_app_after_build():
    container = build_container()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    application.build()

    assert application.app is not None


def test_app_property_raises_if_not_built():
    container = FlotillaContainer(FlotillaSettings({}))
    application = FastApiFlotillaApplication()
    application._attach_container(container=container)

    with pytest.raises(RuntimeError):
        _ = application.app


def test_start_calls_adapter_start():
    container = build_container()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    application.build()
    application.start()

    assert application.started
    assert application.adapter
    assert application.app


def test_start_raises_if_not_built():
    container = build_container()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)

    with pytest.raises(RuntimeError):
        application.start()


def test_routes_are_live_after_start():
    class Handler(HTTPHandler):

        @routes.get("/hello")
        async def hello(self):
            return {"message": "hello"}

    container = FlotillaContainer(FlotillaSettings({}))
    container.register_component(component_name="handler", component=Handler())
    container.build()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    application.build()
    application.start()

    client = TestClient(application.app)
    response = client.get("/hello")

    assert response.status_code == 200
    assert response.json() == {"message": "hello"}


def test_run_uses_defaults_when_no_fastapi_run_config():
    container = FlotillaContainer(FlotillaSettings({}))
    container.build()
    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    application.build()
    application.start()

    with patch("uvicorn.run") as mock_run:
        application.run()

        mock_run.assert_called_once_with(
            application.app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
            reload=False,
        )


def test_run_uses_injected_fastapi_run_config():
    container = FlotillaContainer(FlotillaSettings({}))
    config = FastAPIRunConfig(port=8080, reload=True)
    container.register_component(component_name="fast_api_config", component=config)
    container.build()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    application.build()
    application.start()

    with patch("uvicorn.run") as mock_run:
        application.run()

        mock_run.assert_called_once_with(
            application.app,
            host="127.0.0.1",
            port=8080,
            log_level="info",
            reload=True,
        )


def test_run_kwargs_override_injected_fastapi_run_config():
    container = FlotillaContainer(FlotillaSettings({}))
    config = FastAPIRunConfig(port=8080, reload=True)
    container.register_component(component_name="fast_api_config", component=config)
    container.build()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    application.build()
    application.start()

    with patch("uvicorn.run") as mock_run:
        application.run(port=9000)

        mock_run.assert_called_once_with(
            application.app,
            host="127.0.0.1",
            port=9000,
            log_level="info",
            reload=True,
        )


def test_start_registers_shutdown_hook():
    container = FlotillaContainer(FlotillaSettings({}))
    container.build()
    application = TestFastAPIFlotillaApplication()
    application._attach_container(container=container)
    application.build()
    application.start()

    with TestClient(application.app):
        pass

    assert application.shutdown_called is True
    assert application.shutdown_count == 1


def test_build_does_not_register_shutdown_hook():
    container = FlotillaContainer(FlotillaSettings({}))
    container.build()
    application = TestFastAPIFlotillaApplication()
    application._attach_container(container=container)
    application.build()

    with TestClient(application.app):
        pass

    assert application.shutdown_called is False
    assert application.shutdown_count == 0


def test_shutdown_is_idempotent():
    container = FlotillaContainer(FlotillaSettings({}))
    container.build()
    application = TestFastAPIFlotillaApplication()
    application._attach_container(container=container)
    application.build()
    application.start()

    application.shutdown()
    application.shutdown()

    assert application.shutdown_called is True
    assert application.shutdown_count == 1
