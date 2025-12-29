from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
import jsonschema
from jsonschema import Draft202012Validator

from flotilla.config.config_utils import ConfigUtils
from flotilla.config.configuration_source import ConfigurationSource


# ---------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------

class YamlConfigurationError(RuntimeError):
    pass


class YamlSchemaValidationError(YamlConfigurationError):
    pass


# ---------------------------------------------------------------------
# YamlConfigurationSource
# ---------------------------------------------------------------------

class YamlConfigurationSource:
    """
    ConfigurationSource that loads Flotilla configuration from YAML files.

    Responsibilities:
      - Load flotilla.yml
      - Load flotilla-{env}.yml (if present)
      - Deep-merge (env overrides base)
      - Validate merged config against schema
    """

    def __init__(
        self,
        *,
        config_dir: Path,
        env: Optional[str] = None,
        schema_path: Optional[Path] = None,
    ):
        self._config_dir = Path(config_dir)
        self._env = env.lower() if env else None
        self._schema_path = schema_path

        self._validator = self._load_schema_validator(schema_path)

    # ------------------------------------------------------------
    # ConfigurationSource API
    # ------------------------------------------------------------

    def load(self) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}

        # 1. Load base config
        merged = ConfigUtils.deep_merge(
            merged,
            self._load_yaml("flotilla.yml"),
        )

        # 2. Load environment override
        if self._env:
            merged = ConfigUtils.deep_merge(
                merged,
                self._load_yaml(f"flotilla-{self._env}.yml"),
            )

        # 3. Schema validation (source-level)
        if self._validator:
            self._validate_schema(merged)

        return merged

    # ------------------------------------------------------------
    # YAML loading
    # ------------------------------------------------------------

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        path = self._config_dir / filename
        if not path.exists():
            return {}

        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data or {}
        except yaml.YAMLError as e:
            raise YamlConfigurationError(
                f"Failed to parse YAML file: {path}"
            ) from e

    # ------------------------------------------------------------
    # Schema validation
    # ------------------------------------------------------------

    def _load_schema_validator(
        self,
        schema_path: Optional[Path],
    ) -> Optional[Draft202012Validator]:
        if not schema_path:
            return None

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")

        try:
            with schema_path.open("r", encoding="utf-8") as f:
                schema = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise YamlConfigurationError(
                f"Failed to parse schema file: {schema_path}"
            ) from e

        return Draft202012Validator(schema)

    def _validate_schema(self, config: Dict[str, Any]) -> None:
        errors = sorted(
            self._validator.iter_errors(config),
            key=lambda e: list(e.path),
        )

        if errors:
            messages = []
            for error in errors:
                path = ".".join(str(p) for p in error.path) or "<root>"
                messages.append(f"- {path}: {error.message}")

            raise YamlSchemaValidationError(
                "YAML configuration schema validation failed:\n"
                + "\n".join(messages)
            )
