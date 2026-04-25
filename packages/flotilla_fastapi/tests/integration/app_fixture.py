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


def create_app():
    # create the FlotillaContainer and regiser the HelloHandler
    container = FlotillaContainer(FlotillaSettings({}))
    container.register_component(component_name="handler", component=HelloHandler())
    container.build()

    # create the FlotillaApplication and make FastAPI available
    app = TestApp()
    app._attach_container(container)
    app.build()
    app.start()

    return app


application = create_app()
app = application.app


def main():
    application.run()


if __name__ == "__main__":
    main()
