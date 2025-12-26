from typing import Protocol, Any, Dict

from flotilla.config.config_utils import ConfigUtils

class SecretsResolver(Protocol):
    def resolve(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Return config with secrets resolved"""
        ...


class SimpleSecretsResolver:
    def __init__(self, secrets: Dict[str, str]):
        self.secrets = secrets

    def resolve(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return ConfigUtils.walk_and_replace(config, self._resolve)

    def _resolve(self, value: Any) -> Any:
        if isinstance(value, str) and value.startswith("${secret:"):
            key = value.removeprefix("${secret:").removesuffix("}")
            return self.secrets[key]
        return value
