from __future__ import annotations

from dependency_injector import containers, providers
from typing import List, Optional, Any

from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.container.component_factory import ComponentFactory
from flotilla.container.component_compiler import ComponentCompiler
from flotilla.utils.logger import get_logger
from flotilla.core.errors import FlotillaConfigurationError, ReferenceResolutionError



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

        self._factories: dict[str, ComponentFactory] = {}

        self._pre_compile_hooks = []
        self._post_compile_hooks = []

        self._built = False


    # ----------------------------
    # Public API
    # ----------------------------

    @property
    def config_dict(self) -> dict:
        return self.settings.config


    def register_factory(self, factory_name: str, factory: ComponentFactory):
        """
        Register a factory function that can be referenced by name in config.

        Args:
            buidler_name - The name (key) of the factory function
            factory - The factory function
        """
        logger.info(f"Register factory '{factory_name}'")
        self._factories[factory_name] = factory


    def get_factory(self, factory_name:str) -> Optional[ComponentFactory]:
        """
        Gets the factory for the provided buidler_name, returns None if it doesn't exist

        Args:
            factory_name - The name of the factory to return
        
        Returns:
            The factory function for the name or None if it doesn't exist
        """
        logger.info(f"Get factory for {factory_name}")
        return self._factories.get(factory_name)


    def wire_component(self, *, name: str, factory: ComponentFactory, **kwargs):
        """
        Wire a singleton into the dependency container using an explicit factory function.

        This method performs the actual wiring by registering a singleton provider with
        the dependency-injector container. No validation, configuration lookup, or
        argument processing is performed. All keyword arguments are passed directly to
        the factory function.

        This method is intended for framework-owned or internal components where the
        factory function is known explicitly.

        Args:
            name (str):
                Attribute name under which the singleton provider will be registered on
                the dependency container.
            factory (Componentfactory):
                factory function used to construct the singleton instance.
            **kwargs:
                Keyword arguments passed directly to the factory function.
        """

        logger.info(f"Register singleton {name} with factory function {factory}")
        setattr(self.di, name, providers.Singleton(factory, **kwargs))



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
    

    def resolve_ref(self, ref: dict) -> Any:
        """
        Docstring for resolve_ref
        
        :param self: Description
        :param ref: Description
        :type ref: dict
        :return: Description
        :rtype: Any
        """
        if not isinstance(ref, dict) or "$ref" not in ref:
            return ref

        key = ref["$ref"]
        if not isinstance(key, str):
            raise ReferenceResolutionError("$ref must be a string")


        componnt = self.get(key)
        if componnt is None:
            raise ReferenceResolutionError(f"$ref '{key}' not found in container")
 
            


    def build(self) -> FlotillaContainer:
        """
        Build the DI container from the resolved configuration.

        Build lifecycle:
          1. Pre-compile hooks
          2. Component discovery
          3. Dependency analysis
          4. Component instantiation
          5. Post-compile hooks

        After build completes, the container becomes immutable.
        """

        if self._built:
            raise RuntimeError("FlotillaContainer.build() may only be called once")

        config = self.config_dict

        # ---------------------------
        # Phase 0: pre-compile hooks
        # ---------------------------
        for hook in self._pre_compile_hooks:
            hook(self, config)

        # TODO: Change compiler hooks to be container events that are fired for each step

        # ---------------------------
        # Phase 1–3: compile
        # ---------------------------
        compiler = ComponentCompiler(container=self)

        compiler.discover_components(config)
        compiler.analyze_dependencies()
        compiler.instantiate_components()

        # ---------------------------
        # Phase 4: post-compile hooks
        # ---------------------------
        for hook in self._post_compile_hooks:
            hook(self)

        self._built = True
        return self



