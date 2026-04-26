from typing import Any, Awaitable, Protocol


class SecretResolver(Protocol):
    def resolve(self, secret_key: str) -> Any | None | Awaitable[Any | None]:
        """
        Return a secret value if known, otherwise None.
        Must NOT raise for missing keys.
        """
        ...
