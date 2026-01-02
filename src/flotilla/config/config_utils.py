from typing import Dict, Any, Optional


class ConfigUtils:

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
        if isinstance(obj, dict):
            return {k: ConfigUtils.walk_and_replace(v, fn) for k, v in obj.items()}
        if isinstance(obj, list):
            return [ConfigUtils.walk_and_replace(v, fn) for v in obj]
        return fn(obj)


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
            raise TypeError(
                "resolve_flattened_config requires 'config' to be a dict"
            )

        base_cfg = ConfigUtils._get_at_path(config, base_path)

        # Base missing OR not a dict → treat as unavailable
        if not isinstance(base_cfg, dict):
            return None

        result = dict(base_cfg)

        if override_path:
            override_cfg = ConfigUtils._get_at_path(config, override_path)

            # Only merge if override exists AND is a dict
            if isinstance(override_cfg, dict):
                result = ConfigUtils.deep_merge(result, override_cfg)

        return result
    
    
    @staticmethod
    def _get_at_path(root: Dict[str, Any], path: str) -> Any:
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
