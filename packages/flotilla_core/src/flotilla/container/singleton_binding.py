from flotilla.config.errors import FlotillaConfigurationError
from flotilla.utils.logger import get_logger
from .binding import Binding, call_lifecycle

logger = get_logger(__name__)


class SingletonBinding(Binding):
    def __init__(self, instance):
        self._instance = instance

    async def resolve(self, **kwargs):
        if kwargs:
            logger.error("Singleton binding received resolution parameter keys %s", sorted(kwargs.keys()))
            raise FlotillaConfigurationError("Singleton bindings do not accept resolution parameters")
        logger.debug("Resolve singleton binding instance of %s", type(self._instance))
        return self._instance

    async def startup(self, *, timeout: float | None = None) -> None:
        logger.debug("Start singleton binding instance of %s", type(self._instance))
        await call_lifecycle(self._instance, "startup", timeout=timeout)

    async def shutdown(self, *, timeout: float | None = None) -> None:
        logger.debug("Shut down singleton binding instance of %s", type(self._instance))
        await call_lifecycle(self._instance, "shutdown", timeout=timeout)
