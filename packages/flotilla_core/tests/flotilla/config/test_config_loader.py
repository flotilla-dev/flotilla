import asyncio
import pytest
from typing import Any, Dict

from flotilla.config.config_loader import ConfigLoader, SecretResolutionError
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.config.sources.dict_configuration_source import DictConfigurationSource
from flotilla.config.sources.yaml_configuration_source import YamlConfigurationSource
from flotilla.config.configuration_source import ConfigurationSource
from flotilla.config.secret_resolver import SecretResolver


# ---------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------


class StaticSecretResolver:
    def __init__(self, values: Dict[str, Any]):
        self._values = values

    def resolve(self, secret_key: str) -> Any | None:
        return self._values.get(secret_key)


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


def test_config_loader_merges_sources_last_wins():
    loader = ConfigLoader(
        sources=[
            DictConfigurationSource({"a": 1, "nested": {"x": 1}}),
            DictConfigurationSource({"b": 2, "nested": {"x": 2}}),
        ],
        secrets=[],
    )

    settings = asyncio.run(loader.load())

    assert isinstance(settings, FlotillaSettings)
    assert settings.config["a"] == 1
    assert settings.config["b"] == 2
    assert settings.config["nested"]["x"] == 2


def test_config_loader_merges_yaml_sources_last_file_wins(tmp_path):
    base_config = tmp_path / "application.yml"
    override_config = tmp_path / "dev-override.yml"

    base_config.write_text(
        """
components:
  approval_agent:
    $provider: approval_agent_provider
    model: gpt-4
    temperature: 0.2
  unchanged:
    $provider: unchanged_provider
    value: original
""",
        encoding="utf-8",
    )
    override_config.write_text(
        """
components:
  approval_agent:
    model: gpt-4-mini
""",
        encoding="utf-8",
    )

    loader = ConfigLoader(
        sources=[
            YamlConfigurationSource(path=base_config),
            YamlConfigurationSource(path=override_config),
        ],
        secrets=[],
    )

    settings = asyncio.run(loader.load())

    assert settings.config["components"]["approval_agent"] == {
        "$provider": "approval_agent_provider",
        "model": "gpt-4-mini",
        "temperature": 0.2,
    }
    assert settings.config["components"]["unchanged"]["value"] == "original"


def test_config_loader_resolves_secret_last_non_none_wins():
    loader = ConfigLoader(
        sources=[
            DictConfigurationSource({"api_key": {"$secret": "TOKEN"}}),
        ],
        secrets=[
            StaticSecretResolver({"TOKEN": "first"}),
            StaticSecretResolver({"TOKEN": "second"}),
        ],
    )

    settings = asyncio.run(loader.load())
    assert settings.config["api_key"] == "second"


def test_config_loader_none_does_not_override_real_value():
    loader = ConfigLoader(
        sources=[DictConfigurationSource({"api_key": {"$secret": "TOKEN"}})],
        secrets=[
            StaticSecretResolver({"TOKEN": "valid"}),
            StaticSecretResolver({}),  # returns None
        ],
    )

    settings = asyncio.run(loader.load())
    assert settings.config["api_key"] == "valid"


def test_config_loader_raises_if_secret_unresolved():
    loader = ConfigLoader(
        sources=[DictConfigurationSource({"api_key": {"$secret": "MISSING"}})],
        secrets=[StaticSecretResolver({})],
    )

    with pytest.raises(SecretResolutionError) as exc:
        asyncio.run(loader.load())


def test_config_loader_ignores_non_secret_values():
    loader = ConfigLoader(
        sources=[DictConfigurationSource({"value": "plain-string"})],
        secrets=[],
    )

    settings = asyncio.run(loader.load())
    assert settings.config["value"] == "plain-string"


def test_config_loader_asserts_no_unresolved_secret_refs():
    class PermissiveSecretResolver:
        def resolve(self, key: str):
            return None  # intentionally permissive

    loader = ConfigLoader(
        sources=[DictConfigurationSource({"api_key": {"$secret": "MISSING_KEY"}})],
        secrets=[PermissiveSecretResolver()],
    )

    with pytest.raises(ValueError) as exc:
        asyncio.run(loader.load())

    assert isinstance(exc.value, SecretResolutionError)


def test_secret_scalar_form_is_invalid():
    config = {"api_key": "$secret MY_KEY"}

    loader = ConfigLoader(sources=[DictConfigurationSource(config)])

    with pytest.raises(SecretResolutionError):
        asyncio.run(loader.load())
