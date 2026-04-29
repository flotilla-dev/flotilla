from __future__ import annotations

from typing import Awaitable, Protocol, runtime_checkable


@runtime_checkable
class Startup(Protocol):
    def startup(self) -> None | Awaitable[None]: ...


@runtime_checkable
class Shutdown(Protocol):
    def shutdown(self) -> None | Awaitable[None]: ...
