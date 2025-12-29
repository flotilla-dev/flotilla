from typing import Any, Protocol


class SecretResolutionError(RuntimeError):
    pass

class SecretResolver(Protocol):
    def resolve(self, secret_key: str) -> Any | None:
        """
        Return a secret value if known, otherwise None.
        Must NOT raise for missing keys.
        """
        ...