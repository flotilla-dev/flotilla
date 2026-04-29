from __future__ import annotations

import inspect
from typing import Any, Dict, List, Set, TYPE_CHECKING

from flotilla.config.config_utils import ConfigUtils
from flotilla.config.errors import FlotillaConfigurationError, ReferenceResolutionError
from flotilla.container.constants import REFLECTION_PROVIDER_KEY
from flotilla.utils.logger import get_logger

if TYPE_CHECKING:
    from flotilla.container.flotilla_container import FlotillaContainer

logger = get_logger(__name__)


class ComponentCompiler:
    """
    Canonical $ref rule:
      '$ref <token>' is valid iff FlotillaContainer.get(<token>) succeeds.
      All $ref expressions MUST be resolved during compilation.
      No $ref may reach runtime or factory invocation.
    """

    _TAG_LIST = "$list"
    _TAG_MAP = "$map"
    _TAG_REF = "$ref"
    _TAG_PARAMS = "$params"
    _TAG_PROVIDER = "$provider"
    _TAG_CLASS = "$class"
    _TAG_FACTORY = "$factory"
    _TAG_NAME = "$name"

    def __init__(self, *, container: FlotillaContainer):
        self._container = container

        self._component_defs: Dict[str, Dict[str, Any]] = {}
        self._component_paths: Dict[str, str] = {}
        self._deps: Dict[str, Set[str]] = {}
        self._topo_order: List[str] = []

        self._instantiated: Set[str] = set()
        self._discovered = False
        self._analyzed = False

    # ------------------------------------------------------------------
    # Phase 1 — Discovery
    # ------------------------------------------------------------------

    def discover_components(self, config: Dict[str, Any]) -> None:
        if ConfigUtils.contains_tag(config, tag="$secret"):
            raise FlotillaConfigurationError("Compiler received unresolved $secret")

        logger.info("Discover Flotilla component definitions")
        self._component_defs.clear()
        self._component_paths.clear()
        self._deps.clear()
        self._topo_order.clear()
        self._instantiated.clear()

        self._validate_structure(config, path_parts=[])
        self._walk_for_discovery(config, path_parts=[])
        self._discovered = True
        self._analyzed = False
        logger.info("Discovered %d Flotilla component definition(s)", len(self._component_defs))

    def _walk_for_discovery(self, node: Any, *, path_parts: List[str]) -> None:

        if isinstance(node, dict):

            # --- Directive mappings (not component definitions) ---

            # $ref mapping: do not treat as component, do not recurse
            if self._TAG_REF in node:
                return

            # $list mapping: recurse into list items
            if self._TAG_LIST in node:
                for idx, item in enumerate(node["$list"]):
                    self._walk_for_discovery(
                        item,
                        path_parts=path_parts + [f"$list[{idx}]"],
                    )
                return

            # $map mapping: recurse into map values
            if self._TAG_MAP in node:
                for key, val in node["$map"].items():
                    self._walk_for_discovery(
                        val,
                        path_parts=path_parts + [f"$map.{key}"],
                    )
                return

            # --- Component definition ---

            if self._TAG_PROVIDER in node or self._TAG_CLASS in node or self._TAG_FACTORY in node:
                self._register_component(node=node, path_parts=path_parts)

            # --- Normal recursion ---

            for key, val in node.items():
                if key in {"factory", "ref_name"}:
                    continue
                self._walk_for_discovery(val, path_parts=path_parts + [str(key)])

        elif isinstance(node, list):
            for idx, item in enumerate(node):
                self._walk_for_discovery(
                    item,
                    path_parts=path_parts + [str(idx)],
                )

    def register_component_definition(self, node: Dict[str, Any]) -> None:
        name = node.get(self._TAG_NAME)
        if not isinstance(name, str) or not name:
            raise FlotillaConfigurationError("Python component definitions must include a non-empty $name")
        self._register_component(node=node, path_parts=[name])

    def _register_component(self, *, node: Dict[str, Any], path_parts: List[str]) -> None:
        cfg_path = ".".join(path_parts) if path_parts else ""

        ref_name = node.get(self._TAG_NAME)
        name = ref_name if ref_name else cfg_path

        if name in self._component_defs:
            raise FlotillaConfigurationError(f"Component name '{name}' already exists (declared at {cfg_path})")

        logger.debug("Register component definition '%s' from path '%s'", name, cfg_path)

        # Work on a copy so we don't mutate the original config tree
        node = dict(node)

        # --------------------------------------------
        # Normalize $class → $provider
        # --------------------------------------------
        if self._TAG_CLASS in node:
            class_path = node[self._TAG_CLASS]
            del node[self._TAG_CLASS]

            node[self._TAG_PROVIDER] = REFLECTION_PROVIDER_KEY
            node["class_path"] = class_path
            logger.debug("Normalize $class component '%s' to reflection provider", name)

        # --------------------------------------------
        # Validate provider
        # --------------------------------------------
        provider_name = node.get(self._TAG_FACTORY) if self._TAG_FACTORY in node else node.get(self._TAG_PROVIDER)

        if not isinstance(provider_name, str):
            raise FlotillaConfigurationError(f"{cfg_path}: provider or factory value must be a string")

        provider = self._container.get_provider(provider_name)

        if provider is None:
            raise FlotillaConfigurationError(f"{cfg_path}: no provider registered under key '{provider_name}'")

        if not callable(provider):
            raise FlotillaConfigurationError(f"{cfg_path}: provider or factory '{provider_name}' is not callable")

        self._component_defs[name] = node
        self._component_paths[name] = cfg_path

    def _validate_structure(self, node: Any, path_parts: List[str]) -> None:
        path = ".".join(path_parts) if path_parts else "<root>"

        # Reject scalar directive form
        if isinstance(node, str):
            stripped = node.strip()
            if stripped.startswith("$"):
                raise FlotillaConfigurationError(f"{path}: scalar directive form is not allowed")
            return

        if isinstance(node, dict):

            keys = set(node.keys())

            directive_keys = keys & {
                self._TAG_REF,
                self._TAG_LIST,
                self._TAG_MAP,
            }

            provider_keys = keys & {
                self._TAG_PROVIDER,
                self._TAG_CLASS,
                self._TAG_FACTORY,
            }

            # Directive nodes must contain exactly one key
            if directive_keys:
                if self._TAG_REF in directive_keys:
                    allowed = {self._TAG_REF, self._TAG_PARAMS}
                    if keys - allowed:
                        raise FlotillaConfigurationError(
                            f"{path}: $ref mappings may only contain $ref and $params"
                        )
                    target = node.get(self._TAG_REF)
                    if not isinstance(target, str) or not target:
                        raise FlotillaConfigurationError(f"{path}: $ref must be a non-empty string")
                    params = node.get(self._TAG_PARAMS)
                    if params is not None and not isinstance(params, dict):
                        raise FlotillaConfigurationError(f"{path}: $params must be a mapping")
                    if isinstance(params, dict):
                        for key, value in params.items():
                            self._validate_structure(value, path_parts + [str(key)])
                    return

                if len(keys) != 1:
                    raise FlotillaConfigurationError(
                        f"{path}: directive mappings must contain exactly one directive key"
                    )
                return

            # Provider node: valid component definition
            if provider_keys:
                if len(provider_keys) > 1:
                    raise FlotillaConfigurationError(
                        f"{path}: component definition may contain only one provider directive"
                    )
                return

            # Otherwise recurse normally
            for key, value in node.items():
                self._validate_structure(value, path_parts + [str(key)])

        elif isinstance(node, list):
            raise FlotillaConfigurationError(f"{path}: raw lists are not allowed; use {self._TAG_LIST}")

    # ------------------------------------------------------------------
    # Phase 2 — Dependency Analysis
    # ------------------------------------------------------------------

    def analyze_dependencies(self) -> None:
        if not self._discovered:
            raise RuntimeError("analyze_dependencies called before discovery")

        logger.info("Analyze Flotilla component dependencies")
        self._deps = {name: set() for name in self._component_defs}

        for name, node in self._component_defs.items():
            for dep in self._find_ref_deps(node, owner=name):
                if dep == name:
                    raise FlotillaConfigurationError(f"{self._component_paths[name]}: $ref cannot reference itself")
                if dep not in self._component_defs:
                    if self._container.exists(dep):
                        logger.debug("Dependency '%s' for '%s' is already installed in container", dep, name)
                        continue
                    raise ReferenceResolutionError(f"{self._component_paths[name]}: $ref '{dep}' not found")
                self._deps[name].add(dep)
                logger.debug("Dependency edge '%s' -> '%s'", name, dep)

        self._topo_order = self._toposort_or_raise()
        self._analyzed = True
        logger.info("Dependency analysis complete for %d component definition(s)", len(self._component_defs))
        logger.debug("Component topological order: %s", self._topo_order)

    def _find_ref_deps(self, node: Dict[str, Any], *, owner: str) -> Set[str]:
        deps: Set[str] = set()

        def walk(v: Any) -> None:
            if isinstance(v, dict):
                # Mapping-form $ref
                if self._TAG_REF in v:
                    allowed = {self._TAG_REF, self._TAG_PARAMS}
                    if set(v.keys()) - allowed:
                        raise FlotillaConfigurationError(
                            f"{self._component_paths[owner]}: $ref mapping may only contain '$ref' and '$params'"
                        )
                    target = v[self._TAG_REF]
                    if not isinstance(target, str) or not target:
                        raise ReferenceResolutionError(
                            f"{self._component_paths[owner]}: $ref must be a non-empty string"
                        )
                    deps.add(target)
                    params = v.get(self._TAG_PARAMS)
                    if isinstance(params, dict):
                        walk(params)
                    return

            if isinstance(v, dict):
                if self._TAG_LIST in v:
                    for item in v[self._TAG_LIST]:
                        walk(item)
                    return

                if self._TAG_MAP in v:
                    for item in v[self._TAG_MAP].values():
                        walk(item)
                    return

                for k, vv in v.items():
                    if k in {"factory", "ref_name"}:
                        continue
                    walk(vv)

            elif isinstance(v, list):
                for item in v:
                    walk(item)

        for k, v in node.items():
            if k in {"factory", "ref_name"}:
                continue
            walk(v)

        return deps

    def _toposort_or_raise(self) -> List[str]:
        visited: Set[str] = set()
        visiting: List[str] = []
        order: List[str] = []

        def dfs(n: str) -> None:
            if n in visited:
                return
            if n in visiting:
                idx = visiting.index(n)
                cycle = visiting[idx:] + [n]
                raise FlotillaConfigurationError(f"$ref cycle detected: {' -> '.join(cycle)}")

            visiting.append(n)
            for dep in self._deps.get(n, set()):
                dfs(dep)
            visiting.pop()
            visited.add(n)
            order.append(n)

        for name in self._component_defs:
            dfs(name)

        return order

    # ------------------------------------------------------------------
    # Phase 3 — Instantiation
    # ------------------------------------------------------------------

    async def instantiate_components(self) -> None:
        if not self._analyzed:
            self.analyze_dependencies()

        logger.info("Instantiate Flotilla component graph")
        for name in self._topo_order:
            if self._TAG_FACTORY in self._component_defs[name]:
                await self._install_factory(name)
            else:
                await self._instantiate_component(name)
        logger.info("Flotilla component graph instantiation complete")

    async def _install_factory(self, name: str) -> None:
        if name in self._instantiated:
            return

        node = self._component_defs[name]
        cfg_path = self._component_paths[name]
        logger.debug("Install factory binding '%s' from path '%s'", name, cfg_path)
        provider = self._container.get_provider(node[self._TAG_FACTORY])
        if provider is None:
            raise FlotillaConfigurationError(f"{cfg_path}: unknown factory '{node[self._TAG_FACTORY]}'")

        kwargs = {}
        for key, val in node.items():
            if key in {self._TAG_FACTORY, self._TAG_NAME}:
                continue
            kwargs[key] = await self._materialize_value(val, owner_path=cfg_path, arg_name=key)

        self._container._install_factory_binding(name, provider, **kwargs)
        self._instantiated.add(name)

    async def _instantiate_component(self, name: str) -> None:
        if name in self._instantiated:
            return

        node = self._component_defs[name]
        cfg_path = self._component_paths[name]
        logger.debug("Instantiate component '%s' from path '%s'", name, cfg_path)
        provider = self._container.get_provider(node[self._TAG_PROVIDER])
        if provider is None:
            raise FlotillaConfigurationError(f"{cfg_path}: unknown provider '{node['factory']}'")

        kwargs = {}
        for key, val in node.items():
            if key in {self._TAG_PROVIDER, self._TAG_NAME}:
                continue
            kwargs[key] = await self._materialize_value(val, owner_path=cfg_path, arg_name=key)

        component = provider(**kwargs)
        if inspect.isawaitable(component):
            component = await component

        self._container._install_instance_binding(component_name=name, component=component)
        self._instantiated.add(name)

    async def _materialize_value(self, value, *, owner_path, arg_name):
        # ----- Reject scalar directive forms -----
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("$"):
                raise FlotillaConfigurationError(f"{owner_path}.{arg_name}: scalar directive form is not allowed")
            return value

        # ----- Primitive scalars -----
        if value is None or isinstance(value, (int, float, bool)):
            return value

        # ----- Raw list is illegal -----
        if isinstance(value, list):
            raise FlotillaConfigurationError(
                f"{owner_path}.{arg_name}: raw list values are not allowed; " "use {$list: [...]} instead"
            )

        # ----- Dict handling -----
        if isinstance(value, dict):

            # $ref
            if self._TAG_REF in value:
                allowed = {self._TAG_REF, self._TAG_PARAMS}
                if set(value.keys()) - allowed:
                    raise FlotillaConfigurationError(
                        f"{owner_path}.{arg_name}: $ref mapping may only contain '$ref' and '$params'"
                    )
                target = value[self._TAG_REF]
                if target not in self._component_defs and not self._container.exists(target):
                    raise ReferenceResolutionError(f"{owner_path}.{arg_name}: $ref '{target}' not found")
                if target in self._component_defs and self._TAG_FACTORY in self._component_defs[target]:
                    await self._install_factory(target)
                elif target in self._component_defs:
                    await self._instantiate_component(target)

                params = value.get(self._TAG_PARAMS)
                if params is not None:
                    if not self._container.is_factory_binding(target):
                        raise FlotillaConfigurationError(
                            f"{owner_path}.{arg_name}: $params may only be used with factory bindings"
                        )
                    materialized_params = {
                        k: await self._materialize_value(
                            v,
                            owner_path=owner_path,
                            arg_name=f"{arg_name}.$params.{k}",
                        )
                        for k, v in params.items()
                    }
                    return await self._container.get(target, **materialized_params)

                return await self._container.get(target)

            # $list
            if self._TAG_LIST in value:
                if len(value) != 1:
                    raise FlotillaConfigurationError(
                        f"{owner_path}.{arg_name}: $list mapping must contain only '$list'"
                    )
                return [
                    await self._materialize_value(
                        item,
                        owner_path=owner_path,
                        arg_name=f"{arg_name}[{idx}]",
                    )
                    for idx, item in enumerate(value[self._TAG_LIST])
                ]

            # $map
            if self._TAG_MAP in value:
                if len(value) != 1:
                    raise FlotillaConfigurationError(f"{owner_path}.{arg_name}: $map mapping must contain only '$map'")
                return {
                    k: await self._materialize_value(
                        v,
                        owner_path=owner_path,
                        arg_name=f"{arg_name}.{k}",
                    )
                    for k, v in value[self._TAG_MAP].items()
                }

            # Embedded component definition (mapping containing 'factory')
            if self._TAG_PROVIDER in value or self._TAG_CLASS in value or self._TAG_FACTORY in value:
                embedded_name = f"{owner_path}.{arg_name}"

                # Register component if not already discovered
                if embedded_name not in self._component_defs:
                    self._register_component(
                        node=value,
                        path_parts=embedded_name.split("."),
                    )

                # Ensure dependency analysis is up to date
                if not self._analyzed:
                    self.analyze_dependencies()

                if self._TAG_FACTORY in self._component_defs[embedded_name]:
                    await self._install_factory(embedded_name)
                else:
                    await self._instantiate_component(embedded_name)
                return await self._container.get(embedded_name)

            # ----- Any other dict is illegal -----
            raise FlotillaConfigurationError(
                f"{owner_path}.{arg_name}: raw object values are not allowed; " "use $ref, $list, or $map"
            )

        # ----- Anything else -----
        raise FlotillaConfigurationError(f"{owner_path}.{arg_name}: unsupported value type")
