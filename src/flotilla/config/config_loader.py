from __future__ import annotations

from typing import Any, Dict, List

from flotilla.core.errors import SecretResolutionError, ConfigurationResolutionError
from flotilla.config.config_utils import ConfigUtils
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.config.secret_resolver import (
    SecretResolver
)
from flotilla.config.configuration_source import ConfigurationSource
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """
    Orchestrates configuration loading:

      - loads fragments from ConfigurationSource objects
      - deep-merges fragments (last wins)
      - resolves $config references (config → config)
      - resolves $secret references (config → scalar)
      - constructs FlotillaSettings

    After load(), the returned config is fully materialized:
      - no $config nodes
      - no $secret nodes
    """

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
        logger.info("Start loading Flotilla configuration")

        # --------------------------------------------------
        # 1. Load + merge config fragments
        # --------------------------------------------------
        merged: Dict[str, Any] = {}

        for source in self._sources:
            logger.info(f"Loading configuration fragment from {source}")
            fragment = source.load()
            if fragment:
                merged = ConfigUtils.deep_merge(merged, fragment)

        # --------------------------------------------------
        # 2. Resolve $config references (config → config)
        # --------------------------------------------------
        merged = ConfigUtils.resolve_config_refs(merged, root=merged)
        if ConfigUtils.contains_tag(merged, tag="$config"):
            raise ConfigurationResolutionError("Not all $config keys were properly resolved")

        # --------------------------------------------------
        # 3. Resolve $secret references (config → scalar)
        # --------------------------------------------------
        merged = self._resolve_secrets(merged)
        if ConfigUtils.contains_tag(merged, tag="$secret"):
            raise SecretResolutionError("Not all $secret key were properly resolved")

        logger.info("Finished loading Flotilla configuration")

        # --------------------------------------------------
        # 4. Construct immutable settings object
        # --------------------------------------------------
        return FlotillaSettings(merged)



    # ------------------------------------------------------------
    # Secret resolution (internal)
    # ------------------------------------------------------------

    def _resolve_secrets(self, config: Any) -> Any:
        """
        Walk the config tree and resolve any $secret references.
        """
        return self._walk(config, path=[])

    def _walk(self, value: Any, path: List[str]) -> Any:
        if isinstance(value, dict):
            # $secret object
            if "$secret" in value:
                return self._resolve_secret(value, path)

            # normal dict
            return {
                key: self._walk(val, path + [str(key)])
                for key, val in value.items()
            }

        if isinstance(value, list):
            return [
                self._walk(item, path + [str(idx)])
                for idx, item in enumerate(value)
            ]

        return value

    def _resolve_secret(self, value: Dict[str, Any], path: List[str]) -> Any:
        secret_key = value.get("$secret")

        if not isinstance(secret_key, str):
            location = ".".join(path) if path else "<root>"
            raise SecretResolutionError(
                f"$secret must be a string (at {location})"
            )

        resolved = None
        for resolver in self._secrets:
            result = resolver.resolve(secret_key)  # may raise → allowed
            if result is not None:
                resolved = result  # last non-None wins

        # IMPORTANT:
        # If no resolver resolved it, leave it unresolved.
        return resolved if resolved is not None else value


