from __future__ import annotations

from dependency_injector import containers, providers
from typing import Callable, List, Optional

from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.builders.component_builder import ComponentBuilder
from flotilla.container.contributors.base_contributors import WiringContributor
from flotilla.utils.logger import get_logger



logger = get_logger(__name__)



class FlotillaContainer:
    """
    DI container for Flotilla.
    """

    def __init__(self, settings: FlotillaSettings):
        self.settings = settings

        self.di = containers.DeclarativeContainer()
        self.di.config = providers.Configuration()
        self.di.config.from_dict(settings.config)

        self._builders: dict[str, ComponentBuilder] = {}
        self._contributors: List[WiringContributor] = []

    # ----------------------------
    # Public API
    # ----------------------------

    def register_builder(self, builder_name: str, builder: ComponentBuilder):
        """
        Register a builder function that can be referenced by name in config.

        Args:
            buidler_name - The name (key) of the builder function
            builder - The builder function
        """
        logger.info(f"Register builder '{builder_name}'")
        self._builders[builder_name] = builder


    def get_builder(self, builder_name:str) -> Optional[ComponentBuilder]:
        """
        Gets the builder for the provided buidler_name, returns None if it doesn't exist

        Args:
            builder_name - The name of the builder to return
        
        Returns:
            The builder function for the name or None if it doesn't exist
        """
        logger.info(f"Get builder for {builder_name}")
        return self._builders[builder_name]


    def register_contributor(self, contributor: WiringContributor):
        """
        Register a WiringContributor for use in building the Container

        Args:
            contributor - The WiringContributor to execute
        """
        self._contributors.append(contributor)


    def wire_from_config(self, *, section: str, name: str, config_path: str, **kwargs):
        """
        Wire a config-backed singleton into the dependency container.

        This method reads configuration from the specified configuration section and
        path, resolves the configured builder, and registers a singleton provider
        under the given name.

        The wiring is conditional:
        - If the configuration section does not exist, no wiring is performed.
        - If the configuration path is missing or resolves to no data, no wiring is
        performed.
        - If configuration is present, a builder name is required and must be
        registered on the container.

        This method always injects the following keyword arguments into the builder:
        - ``container``: the dependency-injector container
        - ``config``: the resolved configuration dictionary for this component

        Additional keyword arguments may be provided and will be passed through to
        the builder.

        This method is intended for wiring user-configurable components driven by
        application configuration. Infrastructure components that must always be
        present should be wired using ``wire_infrastructure()`` instead.

        Parameters
        ----------
        section : str
            The top-level configuration section name (e.g. ``"tools"``, ``"agents"``).
        name : str
            The attribute name under which the singleton provider will be registered
            on the dependency container.
        config_path : str
            The configuration key within the section that defines this component.
        **kwargs
            Additional keyword arguments to pass to the builder.

        Raises
        ------
        ValueError
            If configuration is present but no builder is specified, or if the
            specified builder has not been registered on the container. 
        """
        logger.info(f"Register singleton '{name}' from config section '{section}'")

        section_cfg = getattr(self.di.config, section, None)
        if not section_cfg:
            return

        cfg = getattr(section_cfg, config_path, None)
        if not cfg:
            return

        data = cfg()
        if not data:
            return

        builder_name = data.get("builder")
        if not builder_name:
            raise ValueError(
                f"{section}.{config_path}.builder is required"
            )

        builder = self._builders.get(builder_name)
        if not builder:
            raise ValueError(
                f"No builder registered for '{builder_name}'"
            )

        setattr(self.di, name, providers.Singleton(builder, container=self.di, config=data, **kwargs))



    def wire_infrastructure(self, *, name: str, builder: ComponentBuilder, **kwargs):
        """
        Wire an infrastructure singleton into the dependency container.

        This method registers a singleton provider that is not driven by application
        configuration and is expected to be present whenever the container is built.
        Infrastructure components are typically internal framework components such
        as registries, engines, or coordinators.

        The provided builder is invoked with a consistent contract and is always
        supplied the following keyword arguments:
        - ``container``: the dependency-injector container
        - ``config``: an empty configuration dictionary

        Additional keyword arguments may be provided and will be passed through to
        the builder.

        Unlike ``wire_from_config()``, this method does not consult application
        configuration and does not perform conditional wiring. If invoked, the
        infrastructure component is always registered.

        Parameters
        ----------
        name : str
            The attribute name under which the singleton provider will be registered
            on the dependency container.
        builder : ComponentBuilder
            The builder function used to construct the singleton instance.
        **kwargs
            Additional keyword arguments to pass to the builder.

        Raises
        ------
        ValueError
            If the builder is not callable or if wiring fails due to an invalid
            builder invocation.
        """
        setattr(self.di, name,
            providers.Singleton(
                builder,
                container=self.di,
                config={},          # explicit, even if empty
                **kwargs,
            )
        )

    def build(self):
        """
        Finalize the Flotilla dependency container by executing all registered
        wiring contributors.

        This method performs a two-phase build process:

        1. **Contribution phase**:
        All registered contributors are executed in ascending priority order.
        During this phase, contributors perform dependency wiring based on
        configuration and framework conventions. Contributors may fail fast if
        required wiring cannot be completed.

        2. **Validation phase**:
        All contributors are executed again in the same priority order to
        validate that the container is fully and correctly wired. Validation
        ensures that required components are present and that cross-component
        invariants are satisfied.

        The build process is deterministic: contributors are always executed in a
        stable, priority-based order, and validation reflects the results of the
        completed wiring phase.

        This method must be called exactly once before the container is used.
        After a successful build, the container is considered immutable and safe
        for dependency resolution.

        Returns
        -------
        FlotillaContainer
            The fully built container instance.

        Raises
        ------
        Exception
            If any contributor fails during contribution or validation. Errors
            raised during contribution indicate unrecoverable wiring failures,
            while errors raised during validation indicate incomplete or invalid
            wiring.
        """
        logger.info("Building Flotilla DI container")

        ordered = sorted(self._contributors, key=lambda c: c.priority)

        for contributor in ordered:
            contributor.contribute(self)

        for contributor in ordered:
            contributor.validate(self)

        logger.info("✓ Flotilla container build complete")
        return self




