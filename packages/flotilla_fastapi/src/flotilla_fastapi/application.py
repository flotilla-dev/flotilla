from typing import List

from flotilla.flotilla_application import FlotillaApplication
from flotilla_fastapi.adapter import FastAPIAdapter
from flotilla_fastapi.handler import HTTPHandler
from flotilla_fastapi.exception_handler import HTTPExceptionHandler
from flotilla_fastapi.interceptor import HTTPRequestInterceptor
from flotilla.telemetry.telemetry_event import TelemetryEvent
from flotilla_fastapi.config import FastAPIRunConfig

from fastapi import FastAPI
import uvicorn


class FastApiFlotillaApplication(FlotillaApplication):

    def _execute_build(self):
        self.telemetry.emit(
            TelemetryEvent.info(type="", component="FastAPIAdapter", message="Start creation of FastAPIAdapter")
        )

        handlers = self._container.find_instances_by_type(HTTPHandler)
        exception_handlers = self._container.find_instances_by_type(HTTPExceptionHandler)
        interceptors = self._container.find_instances_by_type(HTTPRequestInterceptor)

        self._adapter = self.create_adapter(
            handlers=handlers, exception_handlers=exception_handlers, interceptors=interceptors
        )

        self.telemetry.emit(
            TelemetryEvent.info(type="", component="FastAPIAdapter", message="Finished creation of FastAPIAdapter")
        )

    def create_adapter(
        self,
        *,
        handlers: List[HTTPHandler],
        exception_handlers: List[HTTPExceptionHandler],
        interceptors: List[HTTPRequestInterceptor],
    ) -> FastAPIAdapter:
        return FastAPIAdapter(
            handlers=handlers,
            exception_handlers=exception_handlers,
            interceptors=interceptors,
        )

    def _execute_start(self):
        self.telemetry.emit(
            TelemetryEvent.info(type="", component="FastAPIAdapter", message="Begin start() on FastAPIAdapter")
        )
        self._adapter.start()
        self.adapter.app.add_event_handler("shutdown", self.shutdown)

        self.telemetry.emit(
            TelemetryEvent.info(type="", component="FastAPIAdapter", message="End start() on FastAPIAdapter")
        )

    def _execute_run(self, **kwargs):
        self.telemetry.emit(
            TelemetryEvent.info(type="", component="FastAPIAdapter", message="Begin run() on FastAPIAdapter")
        )
        uvicorn.run(
            self.app,
            **{
                **self._resolve_config().model_dump(),
                **kwargs,
            },
        )

    def _resolve_config(self) -> FastAPIRunConfig:
        configs = self._container.find_instances_by_type(FastAPIRunConfig)
        if len(configs) > 1:
            raise ValueError("Expected at most one FastAPIRunConfig")

        if len(configs) == 1:
            return configs[0]

        return FastAPIRunConfig()

    @property
    def app(self) -> FastAPI:
        self._assert_built()
        return self.adapter.app

    @property
    def adapter(self) -> FastAPIAdapter:
        self._assert_built()
        return self._adapter
