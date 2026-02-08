import pytest
from typing import Any, Dict

from flotilla.config.config_loader import ConfigLoader, SecretResolutionError
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.config.sources.dict_configuration_source import DictConfigurationSource
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

    settings = loader.load()

    assert isinstance(settings, FlotillaSettings)
    assert settings.config["a"] == 1
    assert settings.config["b"] == 2
    assert settings.config["nested"]["x"] == 2


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

    settings = loader.load()
    assert settings.config["api_key"] == "second"


def test_config_loader_none_does_not_override_real_value():
    loader = ConfigLoader(
        sources=[DictConfigurationSource({"api_key": {"$secret": "TOKEN"}})],
        secrets=[
            StaticSecretResolver({"TOKEN": "valid"}),
            StaticSecretResolver({}),  # returns None
        ],
    )

    settings = loader.load()
    assert settings.config["api_key"] == "valid"


def test_config_loader_raises_if_secret_unresolved():
    loader = ConfigLoader(
        sources=[DictConfigurationSource({"api_key": {"$secret": "MISSING"}})],
        secrets=[StaticSecretResolver({})],
    )

    with pytest.raises(SecretResolutionError) as exc:
        loader.load()
    


def test_config_loader_ignores_non_secret_values():
    loader = ConfigLoader(
        sources=[DictConfigurationSource({"value": "plain-string"})],
        secrets=[],
    )

    settings = loader.load()
    assert settings.config["value"] == "plain-string"

# ---------------------------------------------------------------------
# $config resolution
# ---------------------------------------------------------------------

def test_config_loader_resolves_config_reference():
    loader = ConfigLoader(
        sources=[
            DictConfigurationSource(
                {
                    "llm": {
                        "base": {
                            "model": "gpt-4",
                            "temperature": 0.0,
                        }
                    },
                    "agent": {
                        "llm": {
                            "$config": "llm.base",
                        }
                    },
                }
            )
        ],
        secrets=[],
    )

    settings = loader.load()

    assert settings.config["agent"]["llm"] == {
        "model": "gpt-4",
        "temperature": 0.0,
    }


def test_config_loader_resolves_config_with_overrides():
    loader = ConfigLoader(
        sources=[
            DictConfigurationSource(
                {
                    "llm": {
                        "base": {
                            "model": "gpt-4",
                            "temperature": 0.0,
                        }
                    },
                    "agent": {
                        "llm": {
                            "$config": "llm.base",
                            "overrides": {
                                "temperature": 0.7,
                            },
                        }
                    },
                }
            )
        ],
        secrets=[],
    )

    settings = loader.load()

    assert settings.config["agent"]["llm"] == {
        "model": "gpt-4",
        "temperature": 0.7,
    }


def test_config_loader_resolves_config_before_secret():
    loader = ConfigLoader(
        sources=[
            DictConfigurationSource(
                {
                    "llm": {
                        "base": {
                            "model": "gpt-4",
                            "api_key": {"$secret": "OPENAI_KEY"},
                        }
                    },
                    "agent": {
                        "llm": {
                            "$config": "llm.base",
                        }
                    },
                }
            )
        ],
        secrets=[
            StaticSecretResolver({"OPENAI_KEY": "sk-test"}),
        ],
    )

    settings = loader.load()

    assert settings.config["agent"]["llm"] == {
        "model": "gpt-4",
        "api_key": "sk-test",
    }


def test_config_loader_raises_on_invalid_config_reference():
    loader = ConfigLoader(
        sources=[
            DictConfigurationSource(
                {
                    "agent": {
                        "llm": {
                            "$config": "llm.missing",
                        }
                    }
                }
            )
        ],
        secrets=[],
    )

    with pytest.raises(ValueError):
        loader.load()


def test_config_loader_asserts_no_unresolved_secret_refs():
    class PermissiveSecretResolver:
        def resolve(self, key: str):
            return None  # intentionally permissive

    loader = ConfigLoader(
        sources=[
            DictConfigurationSource(
                {
                    "api_key": {
                        "$secret": "MISSING_KEY"
                    }
                }
            )
        ],
        secrets=[PermissiveSecretResolver()],
    )

    with pytest.raises(ValueError) as exc:
        loader.load()
    
    assert isinstance(exc.value, SecretResolutionError)


