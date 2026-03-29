from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response


class HTTPRequestInterceptor(ABC):
    """
    Transport-level HTTP middleware for FastAPIAdapter.

    Implementations are DI-managed and registered as FastAPI
    HTTP middleware during adapter startup.
    """

    @abstractmethod
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        raise NotImplementedError
