from __future__ import annotations

from typing import Any, Dict, List, Set, TYPE_CHECKING

from flotilla.config.config_utils import ConfigUtils
from flotilla.core.errors import FlotillaConfigurationError, ReferenceResolutionError

if TYPE_CHECKING:
    from flotilla.container.flotilla_container import FlotillaContainer

class ComponentCompiler:

    _TAG_REF = "$ref"
    _TAG_LIST = "$list"
    _TAG_DICT = "$dict"

    def __init__(self, *, container: FlotillaContainer):
        self._container = container

        self._root: Dict[str, Any] = {}
        self._component_defs: Dict[str, Dict[str, Any]] = {}
        self._component_paths: Dict[str, str] = {}
        self._deps: Dict[str, Set[str]] = {}
        self._topo_order: List[str] = []

        self._instantiated: Set[str] = set()
        self._building_stack: List[str] = []

        self._discovered = False
        self._analyzed = False

    # ------------------------------------------------------------------
    # Phase 1 — Discovery
    # ------------------------------------------------------------------

    def discover_components(self, config: Dict[str, Any]) -> None:
        if ConfigUtils.contains_tag(config, tag="$config"):
            raise FlotillaConfigurationError(
                "Compiler received unresolved $config"
            )
        if ConfigUtils.contains_tag(config, tag="$secret"):
            raise FlotillaConfigurationError(
                "Compiler received unresolved $secret"
            )

        self._root = config
        self._component_defs.clear()
        self._component_paths.clear()
        self._deps.clear()
        self._topo_order.clear()
        self._instantiated.clear()
        self._building_stack.clear()

        self._walk_for_discovery(config, path_parts=[])
        self._discovered = True
        self._analyzed = False

    def _walk_for_discovery(self, node: Any, *, path_parts: List[str]) -> None:
        if isinstance(node, dict):
            # Guardrail A: factory + $ref is illegal
            if "builder" in node and self._TAG_REF in node:
                cfg_path = ".".join(path_parts) if path_parts else "<root>"
                raise FlotillaConfigurationError(
                    f"{cfg_path}: component cannot declare both 'builder' and '$ref'"
                )

            if "builder" in node:
                self._register_component(node=node, path_parts=path_parts)

            for key, val in node.items():
                if key in {"builder", "ref_name"}:
                    continue
                if key in {self._TAG_REF, self._TAG_LIST, self._TAG_DICT}:
                    continue
                self._walk_for_discovery(val, path_parts=path_parts + [str(key)])

        elif isinstance(node, list):
            for idx, item in enumerate(node):
                self._walk_for_discovery(item, path_parts=path_parts + [str(idx)])

    def _register_component(self, *, node: Dict[str, Any], path_parts: List[str]) -> None:
        cfg_path = ".".join(path_parts) if path_parts else "<root>"

        # Guardrail B: ref_name only allowed on top-level components
        ref_name = node.get("ref_name")
        

        if ref_name is not None:
            if not isinstance(ref_name, str) or not ref_name:
                raise FlotillaConfigurationError(
                    f"{cfg_path}.ref_name must be a non-empty string"
                )
            name = ref_name
        else:
            name = cfg_path

        if name in self._component_defs:
            raise FlotillaConfigurationError(
                f"Component name '{name}' already exists (declared at {cfg_path})"
            )

        builder_name = node.get("builder")
        if not isinstance(builder_name, str) or not builder_name:
            raise FlotillaConfigurationError(
                f"{cfg_path}.builder must be a non-empty string"
            )

        builder = self._container.get_builder(builder_name)

        # Guardrail D: builder must exist and be callable
        if builder is None or not callable(builder):
            raise FlotillaConfigurationError(
                f"{cfg_path}.builder '{builder_name}' is not callable"
            )

        self._component_defs[name] = node
        self._component_paths[name] = cfg_path

    # ------------------------------------------------------------------
    # Phase 2 — Dependency Analysis
    # ------------------------------------------------------------------

    def analyze_dependencies(self) -> None:
        if not self._discovered:
            raise RuntimeError("analyze_dependencies called before discovery")

        self._deps = {name: set() for name in self._component_defs}

        for name, node in self._component_defs.items():
            for dep in self._find_ref_deps(node, owner=name):
                # Guardrail C: direct self-reference
                if dep == name:
                    raise FlotillaConfigurationError(
                        f"{self._component_paths[name]}: $ref cannot reference itself"
                    )

                if dep not in self._component_defs:
                    raise ReferenceResolutionError(
                        f"{self._component_paths[name]}: $ref '{dep}' not found"
                    )
                self._deps[name].add(dep)

        self._topo_order = self._toposort_or_raise()
        self._analyzed = True

    def _find_ref_deps(self, node: Dict[str, Any], *, owner: str) -> Set[str]:
        deps: Set[str] = set()

        def walk(v: Any) -> None:
            if isinstance(v, dict):
                if self._TAG_REF in v:
                    target = v.get(self._TAG_REF)
                    if not isinstance(target, str) or not target:
                        raise ReferenceResolutionError(
                            f"{self._component_paths[owner]}: $ref must be non-empty string"
                        )
                    deps.add(target)
                    return

                if self._TAG_LIST in v:
                    for item in v[self._TAG_LIST]:
                        walk(item)
                    return

                if self._TAG_DICT in v:
                    for item in v[self._TAG_DICT].values():
                        walk(item)
                    return

                for k, vv in v.items():
                    if k in {"builder", "ref_name"}:
                        continue
                    walk(vv)

            elif isinstance(v, list):
                for item in v:
                    walk(item)

        for k, v in node.items():
            if k in {"builder", "ref_name"}:
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
                raise FlotillaConfigurationError(
                    f"$ref cycle detected: {' -> '.join(cycle)}"
                )

            visiting.append(n)
            for dep in sorted(self._deps.get(n, set())):
                dfs(dep)
            visiting.pop()
            visited.add(n)
            order.append(n)

        for name in sorted(self._component_defs):
            dfs(name)

        return order

    # ------------------------------------------------------------------
    # Phase 3 — Instantiation (unchanged)
    # ------------------------------------------------------------------

    def instantiate_components(self) -> None:
        if not self._analyzed:
            self.analyze_dependencies()

        for name in self._topo_order:
            self._instantiate_component(name)

    def _instantiate_component(self, name: str) -> None:
        if name in self._instantiated:
            return

        node = self._component_defs[name]
        cfg_path = self._component_paths[name]

        self._building_stack.append(name)
        try:
            builder = self._container.get_builder(node["builder"])

            kwargs = {}
            for key, val in node.items():
                if key in {"builder", "ref_name"}:
                    continue
                kwargs[key] = self._materialize_value(
                    val, owner_path=cfg_path, arg_name=key
                )

            self._container.wire_component(
                name=name,
                builder=builder,
                **kwargs,
            )
            self._instantiated.add(name)

        finally:
            self._building_stack.pop()

    def _materialize_value(self, value: Any, *, owner_path: str, arg_name: str) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, dict):
            if self._TAG_REF in value:
                target = value[self._TAG_REF]
                self._instantiate_component(target)
                return self._container.get(target)

            if self._TAG_LIST in value:
                return [
                    self._materialize_value(v, owner_path=owner_path, arg_name=f"{arg_name}[{i}]")
                    for i, v in enumerate(value[self._TAG_LIST])
                ]

            if self._TAG_DICT in value:
                return {
                    k: self._materialize_value(v, owner_path=owner_path, arg_name=f"{arg_name}.{k}")
                    for k, v in value[self._TAG_DICT].items()
                }

            if "builder" in value:
                embedded_name = f"{owner_path}.{arg_name}"
                if embedded_name not in self._component_defs:
                    self._register_component(
                        node=value,
                        path_parts=embedded_name.split("."),
                    )
                self._instantiate_component(embedded_name)
                return self._container.get(embedded_name)

            raise FlotillaConfigurationError(
                f"{owner_path}.{arg_name}: raw object values are not allowed"
            )

        if isinstance(value, list):
            raise FlotillaConfigurationError(
                f"{owner_path}.{arg_name}: raw lists are not allowed; use $list"
            )

        raise FlotillaConfigurationError(
            f"{owner_path}.{arg_name}: unsupported value type {type(value).__name__}"
        )
