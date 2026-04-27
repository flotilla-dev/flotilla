import asyncio
import pytest
from pathlib import Path

from flotilla.config.sources.yaml_configuration_source import (
    YamlConfigurationSource,
    YamlConfigurationError,
    YamlSchemaValidationError,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------

def test_yaml_source_loads_file_from_explicit_path(tmp_path: Path):
    config_path = tmp_path / "application.yml"
    write(
        config_path,
        """
flotilla:
  agent_selector:
    type: keyword
"""
    )

    source = YamlConfigurationSource(path=config_path)
    config = asyncio.run(source.load())

    assert config["flotilla"]["agent_selector"]["type"] == "keyword"


def test_yaml_source_missing_file_raises(tmp_path: Path):
    source = YamlConfigurationSource(path=tmp_path / "missing.yml")
    with pytest.raises(FileNotFoundError):
        asyncio.run(source.load())


def test_yaml_source_invalid_yaml_raises(tmp_path: Path):
    config_path = tmp_path / "application.yml"
    write(
        config_path,
        """
flotilla: 
    key: [ unclosed
"""
    )

    source = YamlConfigurationSource(path=config_path)

    with pytest.raises(YamlConfigurationError):
        asyncio.run(source.load())


def test_yaml_source_schema_validation_failure(tmp_path: Path):
    config_path = tmp_path / "application.yml"
    write(
        config_path,
        """
unexpected: true
"""
    )

    write(
        tmp_path / "schema.yml",
        """
type: object
required: [flotilla]
properties:
  flotilla:
    type: object
"""
    )

    source = YamlConfigurationSource(
        path=config_path,
        schema_path=tmp_path / "schema.yml",
    )

    with pytest.raises(YamlSchemaValidationError):
        asyncio.run(source.load())


def test_yaml_source_schema_validation_success(tmp_path: Path):
    config_path = tmp_path / "application.yml"
    write(
        config_path,
        """
flotilla:
  agent_selector:
    type: keyword
"""
    )

    write(
        tmp_path / "schema.yml",
        """
type: object
required: [flotilla]
properties:
  flotilla:
    type: object
"""
    )

    source = YamlConfigurationSource(
        path=config_path,
        schema_path=tmp_path / "schema.yml",
    )

    config = asyncio.run(source.load())
    assert "flotilla" in config
