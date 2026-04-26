import asyncio

from flotilla_fastapi.application import FastApiFlotillaApplication
from flotilla_fastapi.handler import HTTPHandler
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla_fastapi.routes import routes


class HelloHandler(HTTPHandler):

    @routes.get("/hello")
    async def hello(self):
        return {"hello world"}


class TestApp(FastApiFlotillaApplication):
    def _execute_shutdown(self):
        print("SHUTDOWN_HOOK_CALLED", flush=True)


async def build_application():
    # create the FlotillaContainer and regiser the HelloHandler
    container = FlotillaContainer(FlotillaSettings({}))
    container.register_component(component_name="handler", component=HelloHandler())
    await container.build()

    # create the FlotillaApplication and make FastAPI available
    app = TestApp()
    app._attach_container(container)
    await app.build()
    app.start()

    return app


application: TestApp | None = None
_application_lock: asyncio.Lock | None = None


async def get_application() -> TestApp:
    global application, _application_lock

    if application is not None:
        return application

    if _application_lock is None:
        _application_lock = asyncio.Lock()

    async with _application_lock:
        if application is None:
            application = await build_application()

    return application


async def app(scope, receive, send):
    built_application = await get_application()
    await built_application.app(scope, receive, send)


def main():
    global application
    application = asyncio.run(build_application())
    application.run()


if __name__ == "__main__":
    main()
