from typing import Dict, Any

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
