from typing import Protocol, Any, Dict
import yaml
from pathlib import Path
from flotilla.config.config_utils import ConfigUtils

class ConfigurationSource(Protocol):
    def load(self) -> Dict[str, Any]:
        """Return a configuration fragment"""
        ...


class YamlConfigurationSource:
    def __init__(self, config_dir: Path, env: str):
        self.config_dir = Path(config_dir)
        self.env = env.lower()

    def load(self) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}

        for name in ["flotilla", "agents", "tools", "feature_flags"]:
            merged = ConfigUtils.deep_merge(
                merged, self._load_yaml(f"{name}.yml")
            )
            merged = ConfigUtils.deep_merge(
                merged, self._load_yaml(f"{name}.{self.env}.yml")
            )

        return merged

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        path = self.config_dir / filename
        if not path.exists():
            return {}

        with path.open() as f:
            return yaml.safe_load(f) or {}


class DictConfigurationSource:
    def __init__(self, data: Dict[str, Any]):
        self.data = data

    def load(self) -> Dict[str, Any]:
        return self.data
