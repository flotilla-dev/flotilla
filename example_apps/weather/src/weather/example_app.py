from flotilla.flotilla_application import FlotillaApplication
from flotilla.runtime.flotilla_runtime import FlotillaRuntime
from flotilla.thread.thread_service import ThreadService


class ExampleApp(FlotillaApplication):
    runtime: FlotillaRuntime
    thread_service: ThreadService
