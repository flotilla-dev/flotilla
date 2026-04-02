from typing import Any, Dict

from flotilla.config.configuration_source import ConfigurationSource


class DictConfigurationSource:
    """
    ConfigurationSource backed by an in-memory dict.

    Intended for:
      - unit tests
      - programmatic configuration
      - non-file-based setups
    """

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def load(self) -> Dict[str, Any]:
        # Return a shallow copy to prevent mutation
        return dict(self._data)
