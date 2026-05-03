import inspect
import json
from typing import Any, AsyncIterator, List

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, Response

from flotilla_fastapi.handler import HTTPHandler
from flotilla_fastapi.route_definition import RouteDefinition
from flotilla_fastapi.exception_handler import HTTPExceptionHandler
from flotilla_fastapi.interceptor import HTTPRequestInterceptor
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)


class FastAPIAdapter:
    """
    Transport adapter that compiles DI-managed HTTP handlers
    into FastAPI routes at startup.
    """

    def __init__(
        self,
        *,
        handlers: List[HTTPHandler],
        exception_handlers: List[HTTPExceptionHandler],
        interceptors: List[HTTPRequestInterceptor],
        app: FastAPI | None = None,
    ):
        self._handlers = handlers
        self._exception_handlers = exception_handlers
        self._interceptors = interceptors
        self._app = app or FastAPI()

    @property
    def app(self) -> FastAPI:
        return self._app

    def start(self) -> None:
        logger.info(
            "Start FastAPIAdapter binding handlers=%d exception_handlers=%d interceptors=%d",
            len(self._handlers),
            len(self._exception_handlers),
            len(self._interceptors),
        )
        self._bind_interceptors()
        self._bind_routes()
        self._bind_exception_handlers()
        logger.info("FastAPIAdapter binding complete")

    # --------------------------------------------------
    # Route Binding
    # --------------------------------------------------

    def _bind_routes(self) -> None:

        for handler in self._handlers:
            route_defs = self._get_route_methods(handler)
            logger.debug("Discovered %d route(s) on handler %s", len(route_defs), type(handler).__name__)

            for route_def in route_defs:
                endpoint = self._build_endpoint(handler, route_def)
                endpoint = self._apply_wrappers(endpoint, handler, route_def)  # no-op v1
                endpoint = self._wrap_execution(endpoint)
                route_kwargs = dict(route_def.kwargs)
                route_kwargs.setdefault("response_model", None)

                self._app.add_api_route(
                    path=route_def.path,
                    endpoint=endpoint,
                    methods=[route_def.http_method],
                    **route_kwargs,
                )
                logger.info(
                    "Registered FastAPI route %s %s -> %s.%s",
                    route_def.http_method,
                    route_def.path,
                    type(handler).__name__,
                    route_def.method_name,
                )

    def _get_route_methods(self, handler: HTTPHandler) -> List[RouteDefinition]:
        route_defs: list[RouteDefinition] = []

        for name, method in inspect.getmembers(handler, predicate=inspect.ismethod):
            route_meta = getattr(method.__func__, "__flotilla_route__", None)

            if route_meta:
                route_defs.append(
                    RouteDefinition(
                        http_method=route_meta["http_method"],
                        path=route_meta["path"],
                        kwargs=route_meta["kwargs"],
                        method_name=name,
                    )
                )

        return route_defs

    # --------------------------------------------------
    # Endpoint Construction
    # --------------------------------------------------

    def _build_endpoint(self, handler: HTTPHandler, route_def: RouteDefinition):
        method = getattr(handler, route_def.method_name)

        async def endpoint(**kwargs):
            return await method(**kwargs)

        endpoint.__signature__ = inspect.signature(method)
        endpoint.__name__ = method.__name__

        return endpoint

    def _apply_wrappers(self, endpoint, handler, route_def):
        """
        Future extension point for route-level wrappers.
        No-op in v1.
        """
        return endpoint

    def _wrap_execution(self, endpoint):
        async def wrapped(**kwargs):
            logger.debug("Execute FastAPI endpoint %s", endpoint.__name__)
            result = await endpoint(**kwargs)

            if isinstance(result, Response):
                logger.debug("FastAPI endpoint %s returned Response", endpoint.__name__)
                return result

            if self._is_async_iterator(result):
                logger.debug("FastAPI endpoint %s returned async iterator", endpoint.__name__)
                return self._to_streaming_response(result)

            return result

        wrapped.__signature__ = inspect.signature(endpoint)
        wrapped.__name__ = endpoint.__name__

        return wrapped

    # --------------------------------------------------
    # Streaming
    # --------------------------------------------------

    def _is_async_iterator(self, value: Any) -> bool:
        return hasattr(value, "__aiter__")

    def _to_streaming_response(self, iterator: AsyncIterator[Any]) -> StreamingResponse:
        async def stream():
            async for event in iterator:
                logger.debug("Serialize FastAPI streaming event of type %s", type(event).__name__)
                yield self._serialize_stream_event(event)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
        )

    def _serialize_stream_event(self, event: Any) -> str:
        """
        Minimal v1 SSE-ish serialization.

        You can tighten this later to proper SSE framing depending
        on how you want RuntimeEvent exposed.
        """
        return f"data: {json.dumps(event)}\n\n"

    # -----------------------------------
    # Exception Handling
    # -----------------------------------

    def _bind_exception_handlers(self) -> None:
        seen: set[type[Exception]] = set()

        for handler in self._exception_handlers:
            exc_type = handler.exception_type

            if exc_type in seen:
                logger.error("Duplicate HTTPExceptionHandler for %s", exc_type.__name__)
                raise ValueError(f"Duplicate HTTPExceptionHandler for {exc_type.__name__}")

            seen.add(exc_type)

            self._app.add_exception_handler(
                exc_type,
                self._build_exception_handler(handler),
            )
            logger.info("Registered FastAPI exception handler for %s", exc_type.__name__)

    def _build_exception_handler(self, handler: HTTPExceptionHandler):
        async def fastapi_handler(request, exc):
            logger.warning(
                "Handle FastAPI exception %s with %s",
                type(exc).__name__,
                type(handler).__name__,
            )
            return await handler.handle(request, exc)

        return fastapi_handler

    # ----------------------------------------
    # Interceptors
    # ----------------------------------------

    def _bind_interceptors(self) -> None:
        for interceptor in self._interceptors:
            self._register_interceptor(interceptor)

    def _register_interceptor(self, interceptor: HTTPRequestInterceptor) -> None:
        self._app.middleware("http")(interceptor.dispatch)
        logger.info("Registered FastAPI interceptor %s", type(interceptor).__name__)
