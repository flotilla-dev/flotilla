from typing import Any, Dict, Optional
from flotilla.core.errors import ConfigurationResolutionError


class ConfigUtils:
    # ------------------------------------------------------------
    # Existing utilities (UNCHANGED)
    # ------------------------------------------------------------

    @staticmethod
    def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(base)

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ConfigUtils.deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    @staticmethod
    def walk_and_replace(obj: Any, fn):
        replaced = fn(obj)
        if replaced is not obj:
            return replaced

        if isinstance(obj, dict):
            return {k: ConfigUtils.walk_and_replace(v, fn) for k, v in obj.items()}

        if isinstance(obj, list):
            return [ConfigUtils.walk_and_replace(v, fn) for v in obj]

        return obj

    @staticmethod
    def resolve_flattened_config(
        *,
        config: Dict[str, Any],
        base_path: str,
        override_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve and deep-merge configuration from two dot-delimited paths.

        Returns:
            - dict if a mapping is resolved
            - None if base path is missing or not a mapping
        """
        if not isinstance(config, dict):
            raise TypeError("resolve_flattened_config requires 'config' to be a dict")

        base_cfg = ConfigUtils.get_at_path(config, base_path)

        # Base missing OR not a dict → treat as unavailable
        if not isinstance(base_cfg, dict):
            return None

        result = dict(base_cfg)

        if override_path:
            override_cfg = ConfigUtils.get_at_path(config, override_path)

            # Only merge if override exists AND is a dict
            if isinstance(override_cfg, dict):
                result = ConfigUtils.deep_merge(result, override_cfg)

        return result

    @staticmethod
    def get_at_path(root: Dict[str, Any], path: str) -> Any:
        """
        Retrieve a value from a nested dict using a dot-delimited path.
        Returns None if the path does not exist.
        """
        current: Any = root

        for part in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
            if current is None:
                return None

        return current

    # ------------------------------------------------------------
    # NEW: $config resolution
    # ------------------------------------------------------------

    @staticmethod
    def resolve_config_refs(
        config: Any,
        *,
        root: Dict[str, Any],
    ) -> Any:
        """
        Resolve all $config references in the given config tree.

        $config semantics:
          - Must resolve to a dict
          - Optional overrides are deep-merged
          - Resolution is recursive
        """

        def resolver(node: Any) -> Any:
            if isinstance(node, dict) and "$config" in node:
                return ConfigUtils._resolve_config_ref(node, root)
            return node

        return ConfigUtils.walk_and_replace(config, resolver)

    @staticmethod
    def resolve_config_refs(config: Any, *, root: Dict[str, Any]) -> Any:
        return ConfigUtils._resolve_config_refs_internal(
            config,
            root=root,
            resolving=[],
        )

    @staticmethod
    def _resolve_config_refs_internal(
        value: Any,
        *,
        root: Dict[str, Any],
        resolving: list[str],
    ) -> Any:
        def resolver(node: Any) -> Any:
            if isinstance(node, dict) and "$config" in node:
                return ConfigUtils._resolve_config_ref(
                    node,
                    root=root,
                    resolving=resolving,
                )
            return node

        return ConfigUtils.walk_and_replace(value, resolver)

    @staticmethod
    def _resolve_config_ref(
        ref: Dict[str, Any], *, root: Dict[str, Any], resolving: list[str]
    ) -> Dict[str, Any]:
        path = ref.get("$config")

        if not isinstance(path, str):
            raise ConfigurationResolutionError("$config must be a string path")

        # 🚨 Cycle detection
        if path in resolving:
            cycle = " -> ".join(resolving + [path])
            raise ConfigurationResolutionError(f"$config cycle detected: {cycle}")

        base_cfg = ConfigUtils.get_at_path(root, path)
        if not isinstance(base_cfg, dict):
            raise ConfigurationResolutionError(
                f"$config '{path}' must resolve to a config object"
            )

        overrides = ref.get("overrides", {})
        if overrides is not None and not isinstance(overrides, dict):
            raise ConfigurationResolutionError("overrides must be a dict if provided")

        # Push path onto resolution stack
        resolving.append(path)
        try:
            merged = ConfigUtils.deep_merge(base_cfg, overrides or {})
            # Recurse with updated resolving stack
            return ConfigUtils._resolve_config_refs_internal(
                merged,
                root=root,
                resolving=resolving,
            )
        finally:
            # Always pop, even if resolution fails
            resolving.pop()

    @staticmethod
    def contains_tag(value: Any, *, tag: str) -> bool:
        if isinstance(value, dict):
            if tag in value:
                return True

            for val in value.values():
                if ConfigUtils.contains_tag(val, tag=tag):
                    return True

        elif isinstance(value, list):
            for item in value:
                if ConfigUtils.contains_tag(item, tag=tag):
                    return True

        return False
