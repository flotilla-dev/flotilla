import os
from typing import Any

from flotilla.config.secret_resolver import (
    SecretResolutionError,
)
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)

class EnvSecretResolver:
    """Resolve secrets from environment variables."""

    def resolve(self, secret_key: str) -> Any | None:
        if not secret_key:
            return None
        logger.info(f"Look up secret from environment {secret_key}")
        try:
            return os.environ.get(secret_key)
        except Exception as exc:  # extremely rare, but explicit
            raise SecretResolutionError(
                f"Failed to resolve secret from env: {secret_key}"
            ) from exc
