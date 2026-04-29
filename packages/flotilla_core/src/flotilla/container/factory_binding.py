import inspect

from flotilla.config.errors import FlotillaConfigurationError
from flotilla.utils.logger import get_logger
from .binding import Binding, await_if_needed, call_lifecycle

logger = get_logger(__name__)


class FactoryBinding(Binding):
    def __init__(self, factory, **kwargs):
        self._factory = factory
        self._kwargs = kwargs
        self._instances = []
        self._started = False
        self._startup_timeout = None

    @property
    def is_factory(self) -> bool:
        return True

    async def resolve(self, **kwargs):
        resolved_kwargs = {**self._kwargs, **kwargs}
        logger.debug(
            "Resolve factory binding with default keys %s and override keys %s",
            sorted(self._kwargs.keys()),
            sorted(kwargs.keys()),
        )
        instance = await await_if_needed(self._factory(**resolved_kwargs))
        self._instances.append(instance)
        logger.debug("Factory binding created instance of %s", type(instance))

        if self._started:
            try:
                logger.debug("Start factory-created instance of %s", type(instance))
                await call_lifecycle(instance, "startup", timeout=self._startup_timeout)
            except Exception as ex:
                raise FlotillaConfigurationError("Factory-created instance startup failed") from ex

        return instance

    async def startup(self, *, timeout: float | None = None) -> None:
        logger.debug("Start factory binding with %d generated instance(s)", len(self._instances))
        self._started = True
        self._startup_timeout = timeout
        if not inspect.isclass(self._factory):
            await call_lifecycle(self._factory, "startup", timeout=timeout)
        for instance in self._instances:
            await call_lifecycle(instance, "startup", timeout=timeout)

    async def shutdown(self, *, timeout: float | None = None) -> None:
        logger.debug("Shut down factory binding with %d generated instance(s)", len(self._instances))
        errors = []
        for instance in reversed(self._instances):
            try:
                await call_lifecycle(instance, "shutdown", timeout=timeout)
            except Exception as ex:
                errors.append(ex)

        if not inspect.isclass(self._factory):
            try:
                await call_lifecycle(self._factory, "shutdown", timeout=timeout)
            except Exception as ex:
                errors.append(ex)

        self._started = False
        if errors:
            raise FlotillaConfigurationError("Factory binding shutdown failed") from errors[0]
