from __future__ import annotations

import inspect
from typing import List, Optional, Any, Type, TypeVar, Callable, Union, get_origin, get_args, Annotated, get_type_hints
from types import UnionType

from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.container.constants import REFLECTION_PROVIDER_KEY
from flotilla.container.component_provider import ComponentProvider
from flotilla.container.component_compiler import ComponentCompiler
from flotilla.container.binding import Binding
from flotilla.container.singleton_binding import SingletonBinding
from flotilla.container.factory_binding import FactoryBinding
from flotilla.container.providers.reflection_provider import ReflectionProvider
from flotilla.utils.logger import get_logger
from flotilla.config.errors import FlotillaConfigurationError


logger = get_logger(__name__)


class FlotillaContainer:
    """
    DI container for Flotilla.
    """

    def __init__(self, settings: FlotillaSettings):
        self.settings = settings
        self._providers: dict[str, ComponentProvider] = {}
        self._bindings: dict[str, Binding] = {}
        self._component_specs: dict[str, dict[str, Any]] = {}
        self._factory_specs: dict[str, dict[str, Any]] = {}

        self._pre_compile_hooks = []
        self._post_compile_hooks = []

        self._built = False
        self._started = False
        self._shutdown = False

        self.register_provider(REFLECTION_PROVIDER_KEY, ReflectionProvider())

    # ----------------------------
    # Public API
    # ----------------------------

    @property
    def config_dict(self) -> dict:
        return self.settings.config

    def register_provider(self, provider_name: str, provider: ComponentProvider, *, replace: bool = False):
        """
        Register a provider function that can be referenced by name in config.

        Args:
            provider_name - The name (key) of the provider function
            provider - The provider function
            replace - Allow an existing provider to be replaced
        """
        self._assert_not_built()
        if provider_name in self._providers and not replace:
            logger.error("Provider '%s' is already registered", provider_name)
            raise FlotillaConfigurationError(f"Provider '{provider_name}' is already registered")
        if provider_name in self._providers:
            logger.warning("Replacing provider '%s'", provider_name)
        else:
            logger.debug("Register provider '%s'", provider_name)
        self._providers[provider_name] = provider

    def get_provider(self, provider_name: str) -> Optional[ComponentProvider]:
        """
        Gets the provider for the provided buidler_name, returns None if it doesn't exist

        Args:
            provider_name - The name of the provider to return

        Returns:
            The provider function for the name or None if it doesn't exist
        """
        logger.debug("Get provider '%s'", provider_name)
        return self._providers.get(provider_name)

    def define_component(self, component_name: str, *, provider: str | None = None, class_path: str | None = None, **kwargs):
        """
        Register a component definition to be compiled during build.
        """
        self._assert_not_built()
        self._assert_name_available(component_name)
        if (provider is None) == (class_path is None):
            raise FlotillaConfigurationError("define_component requires exactly one of provider or class_path")

        spec = dict(kwargs)
        spec["$name"] = component_name
        if provider is not None:
            spec["$provider"] = provider
        else:
            spec["$class"] = class_path
        logger.debug("Define component '%s'", component_name)
        self._component_specs[component_name] = spec

    def define_factory(self, component_name: str, *, factory: str, **kwargs):
        """
        Register a factory definition to be compiled during build.
        """
        self._assert_not_built()
        self._assert_name_available(component_name)
        spec = dict(kwargs)
        spec["$name"] = component_name
        spec["$factory"] = factory
        logger.debug("Define factory '%s'", component_name)
        self._factory_specs[component_name] = spec

    def _install_instance_binding(self, component_name: str, component: Any):
        """
        Install a resolved singleton binding.

        This is a framework/compiler API, not an application registration API.
        """
        self._assert_not_built()
        if component_name in self._bindings:
            raise FlotillaConfigurationError(f"Component '{component_name}' already registered")

        logger.debug("Install singleton binding '%s'", component_name)
        self._bindings[component_name] = SingletonBinding(component)

    def _install_factory_binding(self, component_name: str, factory: Callable[..., Any], **kwargs):
        """
        Install a resolved factory binding.

        This is a framework/compiler API, not an application registration API.
        """
        self._assert_not_built()
        if component_name in self._bindings:
            raise FlotillaConfigurationError(f"Component '{component_name}' already registered")
        logger.debug("Install factory binding '%s'", component_name)
        self._bindings[component_name] = FactoryBinding(factory, **kwargs)

    async def get(self, name: str, **kwargs) -> Any:
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
            raise FlotillaConfigurationError(f"Component '{name}' not found in container")

        logger.debug("Resolve component '%s' with parameter keys %s", name, sorted(kwargs.keys()))
        return await binding.resolve(**kwargs)

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

    def is_factory_binding(self, name: str) -> bool:
        try:
            return self._bindings[name].is_factory
        except KeyError:
            raise FlotillaConfigurationError(f"Component '{name}' not found in container")

    T = TypeVar("T")

    async def find_instances_by_type(self, base_type: Type[T]) -> List[T]:

        logger.debug("Find all instances of type %s", base_type)
        self._assert_built()

        runtime_types = self._normalize_runtime_types(base_type)

        matches: List[T] = []

        for binding in self._bindings.values():
            try:
                instance = await binding.resolve()
            except Exception:
                continue

            logger.debug("Check if component %s is instance of %s", type(instance), base_type)
            if isinstance(instance, runtime_types):
                matches.append(instance)

        return matches

    async def find_one_by_type(self, base_type: Type[T]) -> T:
        """
        Convenience method to find a single instnace of a particular type on the DI container.  If anything on other
        than a single instacce is found on the DI container a FlotillaConfigurationError is raised.
        """
        logger.debug("Lookup one registered component by type %s", base_type)
        matches = await self.find_instances_by_type(base_type)

        if not matches:
            raise FlotillaConfigurationError(f"No instances of type {base_type.__name__} found in container")

        if len(matches) > 1:
            raise FlotillaConfigurationError(f"Multiple instances of type {base_type.__name__} found: {matches}")

        return matches[0]

    async def create_component(self, cls: Type[T]) -> T:
        """
        Construct a Python class using dependency injection from the container.

        This method allows application code to request construction of an
        arbitrary class whose constructor dependencies are resolved from the
        container by type.

        All constructor parameters MUST have type annotations so the container
        can determine which dependency to inject.

        Dependencies must already exist in the container (Phase-1 behavior).
        If a dependency cannot be found, a FlotillaConfigurationError is raised.

        Parameters
        ----------
        cls : Type[T]
            The class to construct.

        Returns
        -------
        T
            The constructed instance with injected dependencies.

        Raises
        ------
        RuntimeError
            If the container has not been built.

        FlotillaConfigurationError
            If constructor parameters are missing type annotations or if
            dependencies cannot be resolved from the container.
        """

        self._assert_built()

        if not inspect.isclass(cls):
            raise FlotillaConfigurationError(f"create() expected a class, got {type(cls)}")

        try:
            signature = inspect.signature(cls.__init__)
        except (TypeError, ValueError) as ex:
            raise FlotillaConfigurationError(f"Unable to inspect constructor for {cls.__name__}") from ex

        # Resolve annotations (handles string annotations + forward refs)
        type_hints = get_type_hints(cls.__init__)

        kwargs: dict[str, Any] = {}

        for name, param in signature.parameters.items():

            if name == "self":
                continue

            annotation = type_hints.get(name)

            if annotation is None:
                raise FlotillaConfigurationError(
                    f"{cls.__name__}.{name} is missing a type annotation. "
                    "Constructor parameters must be typed for dependency injection."
                )

            origin = get_origin(annotation)
            args = get_args(annotation)

            is_optional = origin in (Union, UnionType) and type(None) in args

            runtime_type = self._normalize_runtime_types(annotation)

            matches = await self.find_instances_by_type(runtime_type)

            if len(matches) == 1:
                kwargs[name] = matches[0]
                continue

            if len(matches) == 0:

                if is_optional:
                    kwargs[name] = None
                    continue

                if param.default is not inspect._empty:
                    kwargs[name] = param.default
                    continue

                raise FlotillaConfigurationError(
                    f"No instances of type {runtime_type} found while constructing {cls.__name__}"
                )

            raise FlotillaConfigurationError(
                f"Multiple instances of type {runtime_type} found while constructing {cls.__name__}"
            )

        try:
            return cls(**kwargs)

        except Exception as ex:
            raise FlotillaConfigurationError(f"Failed to construct {cls.__name__}") from ex

    async def build(self) -> FlotillaContainer:
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
        logger.info("Build FlotillaContainer")

        # ---------------------------
        # Phase 0: pre-compile hooks
        # ---------------------------
        for hook in self._pre_compile_hooks:
            logger.debug("Run pre-compile hook %s", hook)
            result = hook(self, config)
            if inspect.isawaitable(result):
                await result

        # TODO: Change compiler hooks to be container events that are fired for each step

        # ---------------------------
        # Phase 1–3: compile
        # ---------------------------
        compiler = ComponentCompiler(container=self)

        compiler.discover_components(config)
        for spec in self._component_specs.values():
            compiler.register_component_definition(spec)
        for spec in self._factory_specs.values():
            compiler.register_component_definition(spec)
        compiler.analyze_dependencies()
        await compiler.instantiate_components()

        # ---------------------------
        # Phase 4: post-compile hooks
        # ---------------------------
        for hook in self._post_compile_hooks:
            logger.debug("Run post-compile hook %s", hook)
            result = hook(self)
            if inspect.isawaitable(result):
                await result

        self._built = True
        logger.info("FlotillaContainer build complete with %d bindings", len(self._bindings))
        return self

    async def startup(self, *, timeout: float | None = None) -> None:
        self._assert_built()
        if self._started:
            logger.debug("FlotillaContainer startup skipped because it is already started")
            return
        if self._shutdown:
            raise RuntimeError("FlotillaContainer has already been shut down")

        logger.info("Start FlotillaContainer lifecycle")
        started = []
        try:
            for name, binding in self._bindings.items():
                logger.debug("Start binding '%s'", name)
                await binding.startup(timeout=timeout)
                started.append((name, binding))
        except Exception:
            for _, binding in reversed(started):
                try:
                    await binding.shutdown(timeout=timeout)
                except Exception:
                    pass
            raise

        self._started = True
        logger.info("FlotillaContainer startup complete")

    async def shutdown(self, *, timeout: float | None = None) -> None:
        if self._shutdown:
            logger.debug("FlotillaContainer shutdown skipped because it is already shut down")
            return
        logger.info("Shut down FlotillaContainer lifecycle")
        errors = []
        for name, binding in reversed(list(self._bindings.items())):
            try:
                logger.debug("Shut down binding '%s'", name)
                await binding.shutdown(timeout=timeout)
            except Exception as ex:
                logger.warning("Binding '%s' shutdown failed", name, exc_info=True)
                errors.append((name, ex))

        self._started = False
        self._shutdown = True
        if errors:
            names = ", ".join(name for name, _ in errors)
            raise FlotillaConfigurationError(f"Container shutdown failed for bindings: {names}") from errors[0][1]

    # --------------------------
    # Private API helpers
    # --------------------------

    def _assert_not_built(self):
        """Checks to see if the container has not been built.  If it has then it raises a RuntimeError"""
        if self._built:
            raise RuntimeError("FlotillaContainer.build() has already finished and further changes are not allowed")

    def _assert_built(self):
        if not self._built:
            raise RuntimeError("FlotillaContainer.build() must be called before accessing components")

    def _assert_name_available(self, component_name: str) -> None:
        if (
            component_name in self._bindings
            or component_name in self._component_specs
            or component_name in self._factory_specs
        ):
            raise FlotillaConfigurationError(f"Component '{component_name}' already registered")

    def _normalize_runtime_types(self, annotation: Any) -> tuple[type, ...]:
        """
        Convert typing annotations into runtime types suitable for isinstance().
        """

        logger.debug("Normalize runtime annotation %s of type %s", annotation, type(annotation))

        origin = get_origin(annotation)

        # Optional[T], Union[T, None], T | None
        if origin in (Union, UnionType):
            args = [a for a in get_args(annotation) if a is not type(None)]

            if len(args) == 1:
                return self._normalize_runtime_types(args[0])

            return tuple(self._normalize_runtime_types(a) for a in args)

        # Annotated[T, ...]
        if origin is Annotated:
            return self._normalize_runtime_types(get_args(annotation)[0])

        # List[T], Dict[K,V], etc.
        if origin is not None:
            return origin

        return annotation
