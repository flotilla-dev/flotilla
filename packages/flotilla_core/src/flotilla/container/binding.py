from abc import ABC, abstractmethod
import asyncio
import inspect
from typing import Any

from flotilla.container.lifecycle import Shutdown, Startup
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)


class Binding(ABC):
    @abstractmethod
    async def resolve(self, **kwargs) -> Any: ...

    async def startup(self, *, timeout: float | None = None) -> None:
        return None

    async def shutdown(self, *, timeout: float | None = None) -> None:
        return None

    @property
    def is_factory(self) -> bool:
        return False


async def await_if_needed(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def call_lifecycle(target: Any, method_name: str, *, timeout: float | None = None) -> None:
    if method_name == "startup" and not isinstance(target, Startup):
        logger.debug("Lifecycle startup skipped for %s", type(target))
        return
    if method_name == "shutdown" and not isinstance(target, Shutdown):
        logger.debug("Lifecycle shutdown skipped for %s", type(target))
        return

    method = getattr(target, method_name, None)
    if method is None:
        logger.debug("Lifecycle %s missing on %s", method_name, type(target))
        return
    if not callable(method):
        logger.debug("Lifecycle %s is not callable on %s", method_name, type(target))
        return

    logger.debug("Call lifecycle %s on %s", method_name, type(target))
    result = method()
    if inspect.isawaitable(result):
        if timeout is None:
            await result
        else:
            logger.debug("Await lifecycle %s on %s with timeout %s", method_name, type(target), timeout)
            await asyncio.wait_for(result, timeout=timeout)
