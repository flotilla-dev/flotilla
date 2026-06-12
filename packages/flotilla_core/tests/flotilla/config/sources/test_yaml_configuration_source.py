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


def test_yaml_source_validates_against_default_schema(tmp_path: Path):
    config_path = tmp_path / "application.yml"
    write(
        config_path,
        """
flotilla:
  runtime:
    $class: flotilla.runtime.flotilla_runtime.FlotillaRuntime
    $name: runtime
    timeout_ms: 300000
    store:
      $ref: thread_store
  thread_entry_store:
    $class: flotilla.thread.in_memory_store.InMemoryStore
    $name: thread_store
"""
    )

    source = YamlConfigurationSource(path=config_path)
    config = asyncio.run(source.load())

    assert config["flotilla"]["runtime"]["$name"] == "runtime"


def test_yaml_source_default_schema_rejects_raw_list(tmp_path: Path):
    config_path = tmp_path / "application.yml"
    write(
        config_path,
        """
component:
  $provider: simple
  items:
    - a
    - b
"""
    )

    source = YamlConfigurationSource(path=config_path)

    with pytest.raises(YamlSchemaValidationError):
        asyncio.run(source.load())


def test_yaml_source_default_schema_rejects_raw_object_arg(tmp_path: Path):
    config_path = tmp_path / "application.yml"
    write(
        config_path,
        """
component:
  $provider: simple
  options:
    retries: 3
"""
    )

    source = YamlConfigurationSource(path=config_path)

    with pytest.raises(YamlSchemaValidationError):
        asyncio.run(source.load())


def test_yaml_source_default_schema_rejects_scalar_directive_form(tmp_path: Path):
    config_path = tmp_path / "application.yml"
    write(
        config_path,
        """
component:
  $provider: simple
  dep: "$ref other"
"""
    )

    source = YamlConfigurationSource(path=config_path)

    with pytest.raises(YamlSchemaValidationError):
        asyncio.run(source.load())


def test_yaml_source_can_disable_schema_validation(tmp_path: Path):
    config_path = tmp_path / "application.yml"
    write(
        config_path,
        """
component:
  $provider: simple
  items:
    - a
    - b
"""
    )

    source = YamlConfigurationSource(path=config_path, validate_schema=False)
    config = asyncio.run(source.load())

    assert config["component"]["items"] == ["a", "b"]


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


@pytest.mark.parametrize(
    "config_path",
    [
        Path("example_apps/weather/src/weather/app_config/flotilla.yml"),
        Path("example_apps/loan_approval/app/src/loan_server/flotilla.yml"),
    ],
)
def test_example_app_configs_validate_against_default_schema(config_path: Path):
    source = YamlConfigurationSource(path=config_path)

    config = asyncio.run(source.load())

    assert "flotilla" in config
