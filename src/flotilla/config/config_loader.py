from __future__ import annotations

from typing import Any, Dict, List
import re

from flotilla.config.config_utils import ConfigUtils
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.config.secret_resolver import SecretResolver, SecretResolutionError
from flotilla.config.configuration_source import ConfigurationSource

from flotilla.utils.logger import get_logger

logger = get_logger(__name__)
# ---------------------------------------------------------------------
# ConfigLoader
# ---------------------------------------------------------------------

class ConfigLoader:
    """
    Orchestrates configuration loading:
      - loads fragments from sources (ordered)
      - deep-merges fragments (last wins)
      - interpolates secrets
      - constructs FlotillaSettings
    """

    _SECRET_PATTERN = re.compile(r"^\$\{([A-Z0-9_]+)\}$")

    def __init__(
        self,
        *,
        sources: List[ConfigurationSource],
        secrets: List[SecretResolver] | None = None,
    ):
        if not sources:
            raise ValueError("At least one ConfigurationSource is required")

        self._sources = sources
        self._secrets = secrets or []

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def load(self) -> FlotillaSettings:
        logger.info("Start loading of Settings from configuratoin sources")
        # 1. Load + merge config fragments
        merged: Dict[str, Any] = {}
        for source in self._sources:
            logger.info(f"Load configuration fragment from source {source}")
            fragment = source.load()
            if fragment:
                merged = ConfigUtils.deep_merge(merged, fragment)

        # 2. Resolve secrets (full-string interpolation only)
        resolved = self._interpolate_secrets(merged)

        logger.info("Finished loading Settings from configuration sources")
        # 3. Construct immutable, semantically-valid settings
        return FlotillaSettings(resolved)

    # ------------------------------------------------------------
    # Secret interpolation (internal)
    # ------------------------------------------------------------

    def _interpolate_secrets(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return self._walk(config, path=[])

    def _walk(self, value: Any, path: List[str]) -> Any:
        if isinstance(value, dict):
            return {
                key: self._walk(val, path + [str(key)])
                for key, val in value.items()
            }

        if isinstance(value, list):
            return [
                self._walk(item, path + [str(idx)])
                for idx, item in enumerate(value)
            ]

        if isinstance(value, str):
            return self._resolve_if_secret(value, path)

        return value

    def _resolve_if_secret(self, value: str, path: List[str]) -> Any:
        match = self._SECRET_PATTERN.match(value)
        if not match:
            return value

        secret_key = match.group(1)
        resolved = None

        for resolver in self._secrets:
            result = resolver.resolve(secret_key)
            if result is not None:
                resolved = result

        if resolved is None:
            location = ".".join(path) if path else "<root>"
            raise SecretResolutionError(
                f"Secret '{secret_key}' could not be resolved "
                f"(referenced at {location})"
            )

        return resolved
