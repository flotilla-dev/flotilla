from typing import Any, Awaitable, Dict, Protocol


class ConfigurationSource(Protocol):
    def load(self) -> Dict[str, Any] | Awaitable[Dict[str, Any]]:
        """Load and validate a configuration fragment."""
