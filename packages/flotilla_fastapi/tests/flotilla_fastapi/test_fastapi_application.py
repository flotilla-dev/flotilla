import pytest
import httpx
from fastapi import FastAPI
from unittest.mock import patch

from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla_fastapi.application import FastApiFlotillaApplication
from flotilla_fastapi.config import FastAPIRunConfig
from flotilla_fastapi.handler import HTTPHandler
from flotilla_fastapi.routes import routes


async def request(app, method: str, url: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, url, **kwargs)


class TestFastAPIFlotillaApplication(FastApiFlotillaApplication):
    def __init__(self):
        super().__init__()
        self.shutdown_called = False
        self.shutdown_count = 0

    def _execute_shutdown(self) -> None:
        self.shutdown_called = True
        self.shutdown_count += 1


async def build_container(*components):
    container = FlotillaContainer(FlotillaSettings(raw={}))

    for i, component in enumerate(components):
        container._install_instance_binding(component_name=f"component_{i}", component=component)

    await container.build()
    return container


@pytest.mark.asyncio
async def test_build_resolves_fastapi_adapter():
    container = await build_container()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    await application.build()

    assert application.adapter is not None


@pytest.mark.asyncio
async def test_app_property_exposes_fastapi_app_after_build():
    container = await build_container()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    await application.build()

    assert application.app is not None


def test_app_property_raises_if_not_built():
    container = FlotillaContainer(FlotillaSettings({}))
    application = FastApiFlotillaApplication()
    application._attach_container(container=container)

    with pytest.raises(RuntimeError):
        _ = application.app


@pytest.mark.asyncio
async def test_start_calls_adapter_start():
    container = await build_container()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    await application.build()
    application.start()

    assert application.started
    assert application.adapter
    assert application.app


@pytest.mark.asyncio
async def test_start_raises_if_not_built():
    container = await build_container()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)

    with pytest.raises(RuntimeError):
        application.start()


@pytest.mark.asyncio
async def test_routes_are_live_after_start():
    class Handler(HTTPHandler):

        @routes.get("/hello")
        async def hello(self):
            return {"message": "hello"}

    container = FlotillaContainer(FlotillaSettings({}))
    container._install_instance_binding(component_name="handler", component=Handler())
    await container.build()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    await application.build()
    application.start()

    response = await request(application.app, "GET", "/hello")

    assert response.status_code == 200
    assert response.json() == {"message": "hello"}


@pytest.mark.asyncio
async def test_run_uses_defaults_when_no_fastapi_run_config():
    container = FlotillaContainer(FlotillaSettings({}))
    await container.build()
    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    await application.build()
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


@pytest.mark.asyncio
async def test_run_uses_injected_fastapi_run_config():
    container = FlotillaContainer(FlotillaSettings({}))
    config = FastAPIRunConfig(port=8080, reload=True)
    container._install_instance_binding(component_name="fast_api_config", component=config)
    await container.build()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    await application.build()
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


@pytest.mark.asyncio
async def test_run_kwargs_override_injected_fastapi_run_config():
    container = FlotillaContainer(FlotillaSettings({}))
    config = FastAPIRunConfig(port=8080, reload=True)
    container._install_instance_binding(component_name="fast_api_config", component=config)
    await container.build()

    application = FastApiFlotillaApplication()
    application._attach_container(container=container)
    await application.build()
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


@pytest.mark.asyncio
async def test_start_registers_shutdown_hook():
    container = FlotillaContainer(FlotillaSettings({}))
    await container.build()
    application = TestFastAPIFlotillaApplication()
    application._attach_container(container=container)
    await application.build()
    application.start()

    await application.app.router.startup()
    await application.app.router.shutdown()

    assert application.shutdown_called is True
    assert application.shutdown_count == 1


@pytest.mark.asyncio
async def test_build_does_not_register_shutdown_hook():
    container = FlotillaContainer(FlotillaSettings({}))
    await container.build()
    application = TestFastAPIFlotillaApplication()
    application._attach_container(container=container)
    await application.build()

    await application.app.router.startup()
    await application.app.router.shutdown()

    assert application.shutdown_called is False
    assert application.shutdown_count == 0


@pytest.mark.asyncio
async def test_shutdown_is_idempotent():
    container = FlotillaContainer(FlotillaSettings({}))
    await container.build()
    application = TestFastAPIFlotillaApplication()
    application._attach_container(container=container)
    await application.build()
    application.start()

    application.shutdown()
    application.shutdown()

    assert application.shutdown_called is True
    assert application.shutdown_count == 1
