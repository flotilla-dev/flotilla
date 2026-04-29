from __future__ import annotations

from typing import Any, Dict, List
import inspect

from flotilla.config.errors import SecretResolutionError
from flotilla.config.config_utils import ConfigUtils
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.config.secret_resolver import SecretResolver
from flotilla.config.configuration_source import ConfigurationSource
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """
    Orchestrates configuration loading:

      - loads fragments from ConfigurationSource objects
      - deep-merges fragments (last wins)
      - resolves $secret references (config → scalar)
      - constructs FlotillaSettings

    After load(), the returned config is fully materialized:
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

    async def load(self) -> FlotillaSettings:
        logger.info(
            "Load Flotilla configuration from %d source(s) with %d secret resolver(s)",
            len(self._sources),
            len(self._secrets),
        )
        # load from merged sources
        merged = await self._merge_sources()

        # Phase 1: resolve secrets (scalar only)
        merged = await self._resolve_secrets(merged)

        # Phase 2: invariant enforcement
        if ConfigUtils.contains_tag(merged, tag="$secret"):
            raise SecretResolutionError("Not all $secret keys were properly resolved")

        logger.info("Flotilla configuration load complete")
        return FlotillaSettings(merged)

    # ------------------------------------------------------------
    # Secret resolution (internal)
    # ------------------------------------------------------------

    async def _resolve_secrets(self, config: Any) -> Any:
        """
        Walk the config tree and resolve any $secret references.
        """
        return await self._walk(config, path=[])

    async def _walk(self, value: Any, path: List[str]) -> Any:
        location = ".".join(path) if path else "<root>"

        # 🚨 Reject scalar $secret form
        if isinstance(value, str) and value.startswith("$secret"):
            raise SecretResolutionError(
                f"Scalar $secret form is not allowed (at {location}). "
                "Use mapping form: {$secret: NAME}"
            )

        if isinstance(value, dict):
            # $secret object (mapping form)
            if "$secret" in value:
                # Enforce strict schema: only $secret allowed
                if len(value) != 1:
                    raise SecretResolutionError(
                        f"$secret mapping must contain only '$secret' key (at {location})"
                    )
                return await self._resolve_secret(value, path)

            resolved = {}
            for key, val in value.items():
                resolved[key] = await self._walk(val, path + [str(key)])
            return resolved

        if isinstance(value, list):
            resolved = []
            for idx, item in enumerate(value):
                resolved.append(await self._walk(item, path + [str(idx)]))
            return resolved

        return value

    async def _resolve_secret(self, value: Dict[str, Any], path: List[str]) -> Any:
        secret_key = value.get("$secret")
        location = ".".join(path) if path else "<root>"

        if not isinstance(secret_key, str):
            raise SecretResolutionError(f"$secret must be a string (at {location})")

        logger.debug("Resolve secret key '%s' at %s", secret_key, location)
        resolved = None
        for resolver in self._secrets:
            logger.debug(
                "Try secret resolver %s for key '%s' at %s",
                resolver.__class__.__name__,
                secret_key,
                location,
            )
            result = resolver.resolve(secret_key)  # may raise -> allowed
            result = await self._await_if_needed(result)
            if result is not None:
                logger.debug(
                    "Secret key '%s' resolved by %s at %s",
                    secret_key,
                    resolver.__class__.__name__,
                    location,
                )
                resolved = result  # last non-None wins

        if resolved is None:
            logger.error("Unable to resolve secret key '%s' at %s", secret_key, location)
            raise SecretResolutionError(f"Unable to resolve secret {secret_key}")
        return resolved

    async def _merge_sources(self) -> dict:
        """
        Load and merge configuration from all ConfigurationSource instances.

        Merge semantics:
        - Sources are applied in order
        - Later sources override earlier ones
        - Dicts are deep-merged
        - Scalars and lists replace earlier values
        """
        merged: dict = {}

        for idx, source in enumerate(self._sources):
            logger.debug(
                "Load configuration source %d/%d: %s",
                idx + 1,
                len(self._sources),
                source.__class__.__name__,
            )
            data = source.load()
            data = await self._await_if_needed(data)
            if not data:
                logger.debug(
                    "Configuration source %d/%d produced no data: %s",
                    idx + 1,
                    len(self._sources),
                    source.__class__.__name__,
                )
                continue

            merged = ConfigUtils.deep_merge(merged, data)
            logger.debug(
                "Merged configuration source %d/%d: %s",
                idx + 1,
                len(self._sources),
                source.__class__.__name__,
            )

        return merged

    async def _await_if_needed(self, value: Any) -> Any:
        if inspect.isawaitable(value):
            return await value
        return value
