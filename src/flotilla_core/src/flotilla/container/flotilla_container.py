from __future__ import annotations


from typing import List, Optional, Any, Type, TypeVar, Callable

from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.container.component_provider import ComponentProvider
from flotilla.container.component_compiler import ComponentCompiler
from flotilla.container.binding import Binding
from flotilla.container.singleton_binding import SingletonBinding
from flotilla.container.factory_binding import FactoryBinding
from flotilla.utils.logger import get_logger
from flotilla.config.errors import FlotillaConfigurationError, ReferenceResolutionError


logger = get_logger(__name__)


class FlotillaContainer:
    """
    DI container for Flotilla.
    """

    def __init__(self, settings: FlotillaSettings):
        self.settings = settings
        self._providers: dict[str, ComponentProvider] = {}
        self._bindings: dict[str, Binding] = {}

        self._pre_compile_hooks = []
        self._post_compile_hooks = []

        self._built = False

    # ----------------------------
    # Public API
    # ----------------------------

    @property
    def config_dict(self) -> dict:
        return self.settings.config

    def register_provider(self, provider_name: str, provider: ComponentProvider):
        """
        Register a provider function that can be referenced by name in config.

        Args:
            provider_name - The name (key) of the provider function
            provider - The provider function
        """
        self._assert_not_built()
        logger.info(f"Register provider '{provider_name}'")
        self._providers[provider_name] = provider

    def get_provider(self, provider_name: str) -> Optional[ComponentProvider]:
        """
        Gets the provider for the provided buidler_name, returns None if it doesn't exist

        Args:
            provider_name - The name of the provider to return

        Returns:
            The provider function for the name or None if it doesn't exist
        """
        logger.info(f"Get provider for {provider_name}")
        return self._providers.get(provider_name)

    def register_component(
        self,
        *,
        component_name: str,
        component: Any,
    ):
        """ """
        self._assert_not_built()
        if component_name in self._bindings:
            raise FlotillaConfigurationError(
                f"Component '{component_name}' already registered"
            )

        logger.info(f"Register component {component_name}")
        self._bindings[component_name] = SingletonBinding(component)

    def register_factory(
        self, component_name: str, factory: Callable[..., Any], **kwargs
    ):
        """ """
        self._assert_not_built()
        if component_name in self._bindings:
            raise FlotillaConfigurationError(
                f"Component '{component_name}' already registered"
            )
        logger.info(f"Register component factory {component_name}")
        self._bindings[component_name] = FactoryBinding(factory, **kwargs)

    def get(self, name: str) -> Any:
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

        try:
            binding = self._bindings[name]
        except KeyError:
            raise FlotillaConfigurationError(
                f"Component '{name}' not found in container"
            )

        return binding.resolve()

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
        return name in self._bindings

    T = TypeVar("T")

    def find_instances_by_type(self, base_type: Type[T]) -> List[T]:
        """
        Docstring for find_instances_by_type

        :param self: Description
        :param base_type: Description
        :type base_type: Type[T]
        :return: Description
        :rtype: List[T]
        """
        self._assert_built()

        matches: List[T] = []

        for binding in self._bindings.values():
            try:
                instance = binding.resolve()
            except Exception:
                # Defensive: skip bindings that cannot resolve
                continue

            if isinstance(instance, base_type):
                matches.append(instance)

        return matches

    def find_one_by_type(self, base_type: Type[T]) -> T:
        """
        Convenience method to find a single instnace of a particular type on the DI container.  If anything on other
        than a single instacce is found on the DI container a FlotillaConfigurationError is raised.
        """
        matches = self.find_instances_by_type(base_type)

        if not matches:
            raise FlotillaConfigurationError(
                f"No instances of type {base_type.__name__} found in container"
            )

        if len(matches) > 1:
            raise FlotillaConfigurationError(
                f"Multiple instances of type {base_type.__name__} found: {matches}"
            )

        return matches[0]

    '''
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
        '''

    def _assert_not_built(self):
        """Checks to see if the container has not been built.  If it has then it raises a RuntimeError"""
        if self._built:
            raise RuntimeError(
                "FlotillaContainer.build() has already finished and further changes are not allowed"
            )

    def _assert_built(self):
        if not self._built:
            raise RuntimeError(
                "FlotillaContainer.build() must be called before accessing components"
            )

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

        self._assert_not_built()

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
