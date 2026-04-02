from abc import ABC, abstractmethod
from typing import Generic, Type, TypeVar

from starlette.requests import Request
from starlette.responses import Response

E = TypeVar("E", bound=Exception)


class HTTPExceptionHandler(Generic[E], ABC):
    """
    Base transport-level exception handler for FastAPIAdapter.

    Subclasses declare the exception type they handle and
    convert matching exceptions into HTTP responses.
    """

    exception_type: Type[E] = Exception

    @abstractmethod
    async def handle(
        self,
        request: Request,
        exc: E,
    ) -> Response:
        """
        Convert an exception into an HTTP response.
        """
        raise NotImplementedError
