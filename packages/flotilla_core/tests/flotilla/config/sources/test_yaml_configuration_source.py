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

def test_yaml_source_loads_base_file(tmp_path: Path):
    write(
        tmp_path / "flotilla.yml",
        """
flotilla:
  agent_selector:
    type: keyword
"""
    )

    source = YamlConfigurationSource(config_dir=tmp_path)
    config = source.load()

    assert config["flotilla"]["agent_selector"]["type"] == "keyword"


def test_yaml_source_env_override_wins(tmp_path: Path):
    write(
        tmp_path / "flotilla.yml",
        """
llm:
  defaults:
    model: gpt-4
"""
    )

    write(
        tmp_path / "flotilla-test.yml",
        """
llm:
  defaults:
    model: gpt-4-mini
"""
    )

    source = YamlConfigurationSource(
        config_dir=tmp_path,
        env="test",
    )

    config = source.load()
    assert config["llm"]["defaults"]["model"] == "gpt-4-mini"


def test_yaml_source_missing_files_is_ok(tmp_path: Path):
    source = YamlConfigurationSource(config_dir=tmp_path)
    config = source.load()
    assert config == {}


def test_yaml_source_invalid_yaml_raises(tmp_path: Path):
    write(
        tmp_path / "flotilla.yml",
        """
flotilla: 
    key: [ unclosed
"""
    )

    source = YamlConfigurationSource(config_dir=tmp_path)

    with pytest.raises(YamlConfigurationError):
        source.load()


def test_yaml_source_schema_validation_failure(tmp_path: Path):
    write(
        tmp_path / "flotilla.yml",
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
        config_dir=tmp_path,
        schema_path=tmp_path / "schema.yml",
    )

    with pytest.raises(YamlSchemaValidationError):
        source.load()


def test_yaml_source_schema_validation_success(tmp_path: Path):
    write(
        tmp_path / "flotilla.yml",
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
        config_dir=tmp_path,
        schema_path=tmp_path / "schema.yml",
    )

    config = source.load()
    assert "flotilla" in config
