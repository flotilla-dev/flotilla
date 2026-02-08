from typing import Dict, List

from flotilla.container.component_factory import ComponentFactory
from flotilla.container.factory_group import FactoryGroup
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.config.secret_resolver import SecretResolver
from flotilla.config.configuration_source import ConfigurationSource
from flotilla.config.config_loader import ConfigLoader
from flotilla.core.flotilla_runtime import FlotillaRuntime


class FlotillaApplication:
    """
    Top-level lifecycle owner for a Flotilla application.

    FlotillaApplication is responsible for:
      - orchestrating configuration loading via ConfigLoader
      - constructing and building the FlotillaContainer
      - registering application-owned builders and contributors
      - managing application startup and shutdown state

    This class intentionally does NOT:
      - perform dependency injection directly
      - expose configuration loading internals
      - own framework wiring logic

    Configuration is supplied declaratively via ConfigurationSource and
    SecretResolver instances. The resolved configuration is materialized
    as a FlotillaSettings object during startup and passed into the container.

    A FlotillaApplication instance is single-start and single-container:
      - start() builds exactly one container
      - container access is only valid after start()
      - shutdown() invalidates the container

    This class serves as the primary integration point for real runtimes
    (CLI, FastAPI, workers, etc.).
    """
        
    def __init__(self, sources:List[ConfigurationSource], secrets:List[SecretResolver]):
        """
        Create a new FlotillaApplication.

        Args:
            sources:
                Ordered configuration sources used to load application
                configuration. Later sources override earlier ones.
            secrets:
                Ordered secret resolvers used during configuration loading.
                Later resolvers override earlier ones when resolving the
                same secret key.

        The application is created in a non-started state. No configuration
        is loaded and no container is built until start() is called.
        """
        self._builders: Dict[str, ComponentFactory] = {}
        self._loader:ConfigLoader = ConfigLoader(sources=sources, secrets=secrets)
        self._container = None
        self._started = False

    # ----------------------------
    # Extension API (app-owned)
    # ----------------------------

    def register_factory(self, builder_name: str, builder: ComponentFactory):
        """
        Register a named component builder with the application.

        Registered builders are applied to the container during startup
        before contributors are executed.
        """
        self._builders[builder_name] = builder

    def register_factory_group(self, group:FactoryGroup):
        """
        Register a group of component builders.

        All builders provided by the group are registered individually
        under their declared names.
        """
        for name, builder in group.builders().items():
            self.register_factory(name, builder)


    # ----------------------------
    # Build lifecycle
    # ----------------------------

    def _build_container(self, settings:FlotillaSettings) -> FlotillaContainer:
        container = FlotillaContainer(settings)

        # Apply factories
        for name, builder in self._builders.items():
            container.register_factory(name, builder)

        return container.build()
    



    def start(self):
        """
        Start the application and build the Flotilla container.

        This method performs the full startup lifecycle:
        1. Load and merge configuration from the provided ConfigurationSources
        2. Resolve secret references using the provided SecretResolvers
        3. Construct a FlotillaSettings snapshot
        4. Build and validate the FlotillaContainer
        5. Mark the application as started

        After this method completes successfully:
        - the application is considered started
        - the container property becomes accessible
        - all registered builders and contributors have been applied

        Calling start() more than once is not supported.
        """
        settings = self._loader.load()
        self._container = self._build_container(settings=settings)
        self._started = True


    def shutdown(self):
        if not self._started:
            return

        # Optional: graceful teardown hooks later
        self._container = None
        self._started = False


    # ----------------------------
    # Accessors
    # ----------------------------
    
    @property
    def container(self) -> FlotillaContainer:
        """
        Access the built FlotillaContainer.

        Returns:
            The active FlotillaContainer instance.

        Raises:
            RuntimeError:
                If the application has not been started or has been shut down.
        """
        if not self._started:
            raise RuntimeError("Application not started")
        return self._container

    @property
    def started(self) -> bool:
        return self._started
    
    @property
    def runtime(self) -> FlotillaRuntime:
        #TODO change how runtime is returned from the container
        if not self.started:
            raise RuntimeError("Application not started")
        
        return self._container.get("orchestration_engine")
