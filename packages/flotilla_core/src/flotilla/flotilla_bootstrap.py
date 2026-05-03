from typing import Dict, List, Optional, Type

from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.configuration_source import ConfigurationSource
from flotilla.config.secret_resolver import SecretResolver
from flotilla.config.config_loader import ConfigLoader
from flotilla.container.component_provider import ComponentProvider
from flotilla.flotilla_application import FlotillaApplication
from flotilla.config.errors import FlotillaConfigurationError
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)


class FlotillaBootstrap:

    @staticmethod
    async def create(
        cls: Type[FlotillaApplication],
        config_sources: List[ConfigurationSource],
        secret_resolvers: Optional[List[SecretResolver]] = None,
        providers: Optional[Dict[str, ComponentProvider]] = None,
    ) -> FlotillaApplication:

        # ----------------------------
        # Validate application type
        # ----------------------------
        logger.info("Create Flotilla application from bootstrap")

        if not isinstance(cls, type):
            logger.error("Bootstrap cls must be a class, got %s", type(cls))
            raise FlotillaConfigurationError(f"Bootstrap 'cls' must be a class, got {type(cls)}")

        if not issubclass(cls, FlotillaApplication):
            logger.error("Bootstrap cls %s is not a FlotillaApplication subclass", cls.__name__)
            raise FlotillaConfigurationError(f"{cls.__name__} must be a subclass of FlotillaApplication")

        # Normalize optional args
        secret_resolvers = secret_resolvers or []
        providers = providers or {}
        logger.debug(
            "Bootstrap normalized with %d configuration source(s), %d secret resolver(s), %d provider(s)",
            len(config_sources),
            len(secret_resolvers),
            len(providers),
        )

        # ----------------------------
        # Load configuration
        # ----------------------------

        config_loader = ConfigLoader(sources=config_sources, secrets=secret_resolvers)

        settings = await config_loader.load()
        logger.info("Bootstrap configuration loaded")

        # ----------------------------
        # Create container
        # ----------------------------

        container = FlotillaContainer(settings=settings)

        # Register providers
        for name, provider in providers.items():
            logger.debug("Register bootstrap provider '%s'", name)
            container.register_provider(name, provider)

        # Build container
        logger.info("Build and start bootstrap container")
        await container.build()
        await container.startup()

        # ----------------------------
        # Construct application
        # ----------------------------

        app: FlotillaApplication = await container.create_component(cls)
        logger.debug("Bootstrap created application instance %s", type(app).__name__)
        app._attach_container(container=container)
        await app.build()
        app.start()

        logger.info("Bootstrap application %s is ready", type(app).__name__)
        return app
