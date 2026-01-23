from __future__ import annotations

from dependency_injector import containers, providers
from typing import List, Optional, Any

from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.container.component_builder import ComponentBuilder
from flotilla.container.base_contributors import WiringContributor
from flotilla.utils.logger import get_logger
from flotilla.core.errors import FlotillaConfigurationError



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

    @property
    def config_dict(self) -> dict:
        return self.settings.config


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
        return self._builders.get(builder_name)


    def register_contributor(self, contributor: WiringContributor):
        """
        Register a WiringContributor for use in building the Container

        Args:
            contributor - The WiringContributor to execute
        """
        self._contributors.append(contributor)


    def wire_from_config(self, *, section: str, name: str, config_path: str, **kwargs):
        """
        Wire a singleton into the container using application configuration.

        This method conditionally wires a component based on configuration at
        ``<section>.<config_path>``. It extracts the configured builder name, merges
        configuration values with explicitly provided keyword arguments, and delegates
        wiring to ``wire_infrastructure_with_builder()``.

        If the configuration section, path, or data is missing, no wiring is performed.
        If configuration is present, a ``builder`` key is required and must reference a
        registered builder. Explicit keyword arguments always override configuration
        values.

        Args:
            section (str):
                Top-level configuration section (e.g. ``"agents"``, ``"tools"``).
            name (str):
                Attribute name under which the singleton provider will be registered on
                the dependency container.
            config_path (str):
                Key within the configuration section that defines this component.
            **kwargs:
                Explicit keyword arguments passed to the builder. These values override
                any corresponding values provided by configuration.

        Raises:
            FlotillaConfigurationError:
                If configuration is present but no builder is specified, or if the
                configured builder is not registered on the container.
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
            raise FlotillaConfigurationError(f"{section}.{config_path}.builder is required"
        )
        data.pop("builder", None)

        # Merge: explicit kwargs override config
        merged_kwargs = {**data, **kwargs}

        self.wire_infrastructure_with_builder(name=name, builder_name=builder_name, **merged_kwargs)


    def wire_infrastructure_with_builder(self, *, name: str, builder_name: str, **kwargs):
        """
        Wire a singleton into the container using a builder resolved by name.

        This method resolves a builder function from the container's builder registry,
        validates that it exists, and delegates wiring to ``wire_infrastructure()``.
        All parameters required by the builder must be supplied explicitly via
        keyword arguments.

        This method does not consult application configuration and always performs
        wiring when invoked.

        Args:
            name (str):
                Attribute name under which the singleton provider will be registered on
                the dependency container.
            builder_name (str):
                Name of the builder function registered on the container.
            **kwargs:
                Keyword arguments passed directly to the builder function.

        Raises:
            FlotillaConfigurationError:
                If the specified builder name is not registered on the container.
        """
        logger.info(f"Register infrstructure {name} with builder name {builder_name}")
        builder = self.get_builder(builder_name)
        if not builder:
            raise FlotillaConfigurationError(
                f"Unable to wire infrastructure '{name}' with unknown builder '{builder_name}'"
            )


        self.wire_infrastructure(name=name, builder=builder, **kwargs)




    def wire_infrastructure(self, *, name: str, builder: ComponentBuilder, **kwargs):
        """
        Wire a singleton into the dependency container using an explicit builder function.

        This method performs the actual wiring by registering a singleton provider with
        the dependency-injector container. No validation, configuration lookup, or
        argument processing is performed. All keyword arguments are passed directly to
        the builder function.

        This method is intended for framework-owned or internal components where the
        builder function is known explicitly.

        Args:
            name (str):
                Attribute name under which the singleton provider will be registered on
                the dependency container.
            builder (ComponentBuilder):
                Builder function used to construct the singleton instance.
            **kwargs:
                Keyword arguments passed directly to the builder function.
        """

        logger.info(f"Register singleton {name} with builder function {builder}")
        setattr(self.di, name, providers.Singleton(builder, **kwargs))


    def get(self, name: str) -> Optional[Any]:
        """
        Retrieve a resolved component from the container if it exists.

        This method safely checks whether a component has been wired into the
        internal dependency container under the given name and, if so,
        returns the instantiated singleton.

        If the component is not present, ``None`` is returned.

        Calling this method MAY instantiate the component if it has not
        already been constructed. Callers should avoid invoking this method
        during validation phases if instantiation is undesirable.

        Parameters
        ----------
        name : str
            The attribute name of the component on the container.

        Returns
        -------
        Optional[Any]
            The resolved component instance, or ``None`` if the component is
            not present.
        """
        provider = getattr(self.di, name, None)
        if provider is None:
            return None

        try:
            return provider()
        except Exception:
            logger.exception(f"Failed to resolve component '{name}'")
            raise

    def exists(self, name: str) -> bool:
        """
        Check whether a component has been wired into the container.

        This method verifies that a component provider exists on the internal
        dependency container under the given name. It does NOT instantiate
        the component.

        Parameters
        ----------
        name : str
            The attribute name of the component on the container.

        Returns
        -------
        bool
            True if the component is present, False otherwise.
        """
        return hasattr(self.di, name)

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

        logger.info("Execute WiringContributors in priorty order")
        for contributor in ordered:
            logger.info(f"Call contribute on WiringContributor {contributor.__class__}")
            contributor.contribute(self)

        logger.info("Validate container wiring in priortiy order")
        for contributor in ordered:
            logger.info(f"Call validate on WiringContributor {contributor.__class__}")
            contributor.validate(self)

        logger.info("✓ Flotilla container build complete")
        return self




