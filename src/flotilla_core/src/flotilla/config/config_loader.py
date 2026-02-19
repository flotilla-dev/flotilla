from __future__ import annotations

from typing import Any, Dict, List
import copy

from flotilla.core.errors import SecretResolutionError, ConfigurationResolutionError
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
        # load from merged sources
        merged = self._merge_sources()

        # Phase 1: resolve secrets (scalar only)
        merged = self._resolve_secrets(merged)

        # Phase 2: resolve $config (structural, recursive)
        merged = self._resolve_config_nodes(merged, root=merged)

        # Phase 3: invariant enforcement
        if ConfigUtils.contains_tag(merged, tag="$secret"):
            raise SecretResolutionError("Not all $secret keys were properly resolved")

        if ConfigUtils.contains_tag(merged, tag="$config"):
            raise ConfigurationResolutionError(
                "Not all $config keys were properly resolved"
            )

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
                return self._resolve_secret(value, path)

            return {
                key: self._walk(val, path + [str(key)]) for key, val in value.items()
            }

        if isinstance(value, list):
            return [
                self._walk(item, path + [str(idx)]) for idx, item in enumerate(value)
            ]

        return value

    def _resolve_secret(self, value: Dict[str, Any], path: List[str]) -> Any:
        secret_key = value.get("$secret")

        if not isinstance(secret_key, str):
            location = ".".join(path) if path else "<root>"
            raise SecretResolutionError(f"$secret must be a string (at {location})")

        resolved = None
        for resolver in self._secrets:
            result = resolver.resolve(secret_key)  # may raise → allowed
            if result is not None:
                resolved = result  # last non-None wins

        if resolved is None:
            raise SecretResolutionError(f"Unable to resolve secret {secret_key}")
        return resolved

    def _resolve_config_nodes(self, node: Any, *, root: Dict[str, Any]) -> Any:
        """
        Resolve $config directives.

        Supported forms:
        1. Scalar: "$config path.to.node"
        2. Mapping:
            {
                "$config": "path.to.node",
                "overrides": { ... }   # optional
            }
        """

        if isinstance(node, str) and node.startswith("$config"):
            raise ConfigurationResolutionError(
                f"Scalar $config form is not allowed. Use {{$config: path}}"
            )

        # ----------------------------
        # Scalar form: "$config path"
        # ----------------------------
        if isinstance(node, str) and node.startswith("$config"):
            raise ConfigurationResolutionError(
                f"Scalar $config form is not allowed. Use {{$config: path}}"
            )

        # ----------------------------
        # Mapping form with overrides
        # ----------------------------
        if isinstance(node, dict) and "$config" in node:
            allowed_keys = {"$config", "overrides"}
            illegal = set(node.keys()) - allowed_keys
            if illegal:
                raise ConfigurationResolutionError(
                    f"$config mapping may only contain $config and overrides "
                    f"(found extra keys: {sorted(illegal)})"
                )

            path = node["$config"]
            if not isinstance(path, str):
                raise ConfigurationResolutionError(
                    "$config value must be a string path"
                )

            base = ConfigUtils.get_at_path(root, path)
            if base is None:
                raise ConfigurationResolutionError(
                    f"$config reference '{path}' could not be resolved"
                )

            # Deep copy base config
            result = copy.deepcopy(base)

            # Apply overrides (if present)
            overrides = node.get("overrides")
            if overrides is not None:
                if not isinstance(overrides, dict):
                    raise ConfigurationResolutionError("overrides must be a mapping")
                result = ConfigUtils.deep_merge(result, overrides)

            # Recurse to handle nested $config
            return self._resolve_config_nodes(result, root=root)

        # ----------------------------
        # Recursive descent
        # ----------------------------
        if isinstance(node, dict):
            return {
                k: self._resolve_config_nodes(v, root=root) for k, v in node.items()
            }

        if isinstance(node, list):
            return [self._resolve_config_nodes(v, root=root) for v in node]

        return node

    def _merge_sources(self) -> dict:
        """
        Load and merge configuration from all ConfigurationSource instances.

        Merge semantics:
        - Sources are applied in order
        - Later sources override earlier ones
        - Dicts are deep-merged
        - Scalars and lists replace earlier values
        """
        merged: dict = {}

        for source in self._sources:
            data = source.load()
            if not data:
                continue

            merged = ConfigUtils.deep_merge(merged, data)

        return merged
