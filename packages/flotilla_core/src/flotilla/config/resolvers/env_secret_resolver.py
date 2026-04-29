import os
from typing import Any

from flotilla.config.errors import SecretResolutionError
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)


class EnvSecretResolver:
    """Resolve secrets from environment variables."""

    async def resolve(self, secret_key: str) -> Any | None:
        if not secret_key:
            return None
        logger.debug("Look up secret key '%s' from environment", secret_key)
        try:
            return os.getenv(secret_key)
        except Exception as exc:  # extremely rare, but explicit
            raise SecretResolutionError(
                f"Failed to resolve secret from env: {secret_key}"
            ) from exc
