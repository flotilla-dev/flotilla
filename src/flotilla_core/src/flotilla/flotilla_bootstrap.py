from typing import Dict, List, Optional, Type

from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.configuration_source import ConfigurationSource
from flotilla.config.secret_resolver import SecretResolver
from flotilla.config.config_loader import ConfigLoader
from flotilla.container.component_provider import ComponentProvider
from flotilla.flotilla_application import FlotillaApplication
from flotilla.config.errors import FlotillaConfigurationError


class FlotillaBootstrap:

    @staticmethod
    def create(
        cls: Type[FlotillaApplication],
        config_sources: List[ConfigurationSource],
        secret_resolvers: Optional[List[SecretResolver]] = None,
        providers: Optional[Dict[str, ComponentProvider]] = None,
    ) -> FlotillaApplication:

        # ----------------------------
        # Validate application type
        # ----------------------------

        if not isinstance(cls, type):
            raise FlotillaConfigurationError(f"Bootstrap 'cls' must be a class, got {type(cls)}")

        if not issubclass(cls, FlotillaApplication):
            raise FlotillaConfigurationError(f"{cls.__name__} must be a subclass of FlotillaApplication")

        # Normalize optional args
        secret_resolvers = secret_resolvers or []
        providers = providers or {}

        # ----------------------------
        # Load configuration
        # ----------------------------

        config_loader = ConfigLoader(sources=config_sources, secrets=secret_resolvers)

        settings = config_loader.load()

        # ----------------------------
        # Create container
        # ----------------------------

        container = FlotillaContainer(settings=settings)

        # Register providers
        for name, provider in providers.items():
            container.register_provider(name, provider)

        # Build container
        container.build()

        # ----------------------------
        # Construct application
        # ----------------------------

        app: FlotillaApplication = container.create_component(cls)
        app._attach_container(container=container)
        app.build()
        app.start()

        return app
