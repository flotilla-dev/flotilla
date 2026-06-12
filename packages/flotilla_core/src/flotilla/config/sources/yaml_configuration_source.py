from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from flotilla.config.configuration_source import ConfigurationSource
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)

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
    ConfigurationSource that loads one explicit Flotilla YAML configuration file.

    Responsibilities:
      - Load the configured YAML file
      - Validate the loaded config against an optional schema

    Compose multiple YAML files by passing multiple YamlConfigurationSource
    instances to ConfigLoader. Sources are merged in order by ConfigLoader, so
    later files override earlier files.
    """

    def __init__(
        self,
        *,
        path: Path,
        validate_schema: bool = True,
        schema_path: Optional[Path] = None,
    ):
        self._path = Path(path)
        self._schema_path = Path(schema_path) if schema_path else None

        self._validator = self._load_schema_validator(
            validate_schema=validate_schema,
            schema_path=self._schema_path,
        )

    # ------------------------------------------------------------
    # ConfigurationSource API
    # ------------------------------------------------------------

    async def load(self) -> Dict[str, Any]:
        logger.info(f"Start loading configuration from YAML file '{self._path}'")

        config = self._load_yaml()

        if self._validator:
            self._validate_schema(config)
        
        logger.info(f"Finished loading configuration from YAML file '{self._path}'")
        return config

    # ------------------------------------------------------------
    # YAML loading
    # ------------------------------------------------------------

    def _load_yaml(self) -> Dict[str, Any]:
        logger.info(f"Check if path {self._path} exists")
        if not self._path.exists():
            raise FileNotFoundError(f"YAML configuration file not found: {self._path}")
        
        logger.info(f"Load YAML Configuration from '{self._path}'")
        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data or {}
        except yaml.YAMLError as e:
            raise YamlConfigurationError(
                f"Failed to parse YAML file: {self._path}"
            ) from e

    # ------------------------------------------------------------
    # Schema validation
    # ------------------------------------------------------------

    def _load_schema_validator(
        self,
        *,
        validate_schema: bool,
        schema_path: Optional[Path],
    ) -> Optional[Draft202012Validator]:
        if not validate_schema:
            return None

        if not schema_path:
            return self._load_default_schema_validator()

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

    def _load_default_schema_validator(self) -> Draft202012Validator:
        try:
            schema_resource = files("flotilla.config.schema").joinpath("flotilla.schema.yml")
            with schema_resource.open("r", encoding="utf-8") as f:
                schema = yaml.safe_load(f)
        except (FileNotFoundError, ModuleNotFoundError) as e:
            raise FileNotFoundError("Packaged Flotilla schema not found") from e
        except yaml.YAMLError as e:
            raise YamlConfigurationError("Failed to parse packaged Flotilla schema") from e

        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as e:
            raise YamlConfigurationError("Packaged Flotilla schema is invalid") from e

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
