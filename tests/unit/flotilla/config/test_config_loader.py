import pytest
from typing import Any, Dict

from flotilla.config.config_loader import ConfigLoader, SecretResolutionError
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.config.configuration_source import ConfigurationSource
from flotilla.config.secret_resolver import SecretResolver


# ---------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------

class DictSource:
    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def load(self) -> Dict[str, Any]:
        return self._data


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
            DictSource({"a": 1, "nested": {"x": 1}}),
            DictSource({"b": 2, "nested": {"x": 2}}),
        ],
        secrets=[],
    )

    settings = loader.load()

    assert isinstance(settings, FlotillaSettings)
    assert settings.config["a"] == 1
    assert settings.config["b"] == 2
    assert settings.config["nested"]["x"] == 2


def test_config_loader_resolves_secret_last_non_none_wins():
    loader = ConfigLoader(
        sources=[
            DictSource({"api_key": "${TOKEN}"}),
        ],
        secrets=[
            StaticSecretResolver({"TOKEN": "first"}),
            StaticSecretResolver({"TOKEN": "second"}),
        ],
    )

    settings = loader.load()
    assert settings.config["api_key"] == "second"


def test_config_loader_none_does_not_override_real_value():
    loader = ConfigLoader(
        sources=[DictSource({"api_key": "${TOKEN}"})],
        secrets=[
            StaticSecretResolver({"TOKEN": "valid"}),
            StaticSecretResolver({}),  # returns None
        ],
    )

    settings = loader.load()
    assert settings.config["api_key"] == "valid"


def test_config_loader_raises_if_secret_unresolved():
    loader = ConfigLoader(
        sources=[DictSource({"api_key": "${MISSING}"})],
        secrets=[StaticSecretResolver({})],
    )

    with pytest.raises(SecretResolutionError) as exc:
        loader.load()

    assert "MISSING" in str(exc.value)


def test_config_loader_ignores_non_secret_strings():
    loader = ConfigLoader(
        sources=[DictSource({"value": "plain-string"})],
        secrets=[],
    )

    settings = loader.load()
    assert settings.config["value"] == "plain-string"
