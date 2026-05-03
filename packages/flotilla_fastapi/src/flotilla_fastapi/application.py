from typing import List

from flotilla.flotilla_application import FlotillaApplication
from flotilla_fastapi.adapter import FastAPIAdapter
from flotilla_fastapi.handler import HTTPHandler
from flotilla_fastapi.exception_handler import HTTPExceptionHandler
from flotilla_fastapi.interceptor import HTTPRequestInterceptor
from flotilla_fastapi.config import FastAPIRunConfig
from flotilla.utils.logger import get_logger

from fastapi import FastAPI
import uvicorn

logger = get_logger(__name__)


class FastApiFlotillaApplication(FlotillaApplication):

    async def _execute_build(self):
        logger.info("Build FastAPI adapter")

        handlers = await self._container.find_instances_by_type(HTTPHandler)
        exception_handlers = await self._container.find_instances_by_type(HTTPExceptionHandler)
        interceptors = await self._container.find_instances_by_type(HTTPRequestInterceptor)
        self._fastapi_run_config = await self._resolve_config()
        logger.debug(
            "FastAPI adapter dependencies resolved: handlers=%d exception_handlers=%d interceptors=%d",
            len(handlers),
            len(exception_handlers),
            len(interceptors),
        )

        self._adapter = self.create_adapter(
            handlers=handlers, exception_handlers=exception_handlers, interceptors=interceptors
        )

        logger.info("FastAPI adapter build complete")

    def create_adapter(
        self,
        *,
        handlers: List[HTTPHandler],
        exception_handlers: List[HTTPExceptionHandler],
        interceptors: List[HTTPRequestInterceptor],
    ) -> FastAPIAdapter:
        logger.debug(
            "Create FastAPIAdapter with %d handler(s), %d exception handler(s), %d interceptor(s)",
            len(handlers),
            len(exception_handlers),
            len(interceptors),
        )
        return FastAPIAdapter(
            handlers=handlers,
            exception_handlers=exception_handlers,
            interceptors=interceptors,
        )

    def _execute_start(self):
        logger.info("Start FastAPI adapter")
        self._adapter.start()
        self.adapter.app.add_event_handler("shutdown", self.shutdown)

        logger.info("FastAPI adapter started")

    def _execute_run(self, **kwargs):
        run_config = {**self._fastapi_run_config.model_dump(), **kwargs}
        logger.info(
            "Run FastAPI application on %s:%s reload=%s log_level=%s",
            run_config.get("host"),
            run_config.get("port"),
            run_config.get("reload"),
            run_config.get("log_level"),
        )
        uvicorn.run(
            self.app,
            **run_config,
        )

    async def _resolve_config(self) -> FastAPIRunConfig:
        configs = await self._container.find_instances_by_type(FastAPIRunConfig)
        if len(configs) > 1:
            logger.error("Expected at most one FastAPIRunConfig, found %d", len(configs))
            raise ValueError("Expected at most one FastAPIRunConfig")

        if len(configs) == 1:
            logger.debug("Use configured FastAPIRunConfig")
            return configs[0]

        logger.debug("Use default FastAPIRunConfig")
        return FastAPIRunConfig()

    @property
    def app(self) -> FastAPI:
        self._assert_built()
        return self.adapter.app

    @property
    def adapter(self) -> FastAPIAdapter:
        self._assert_built()
        return self._adapter
