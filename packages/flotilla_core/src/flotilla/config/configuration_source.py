from typing import Any, Dict, Protocol


class ConfigurationSource(Protocol):
    def load(self) -> Dict[str, Any]:
        """Load and validate a configuration fragment."""