import asyncio
import pytest
from typing import Any, Dict

from flotilla.config.config_loader import ConfigLoader, SecretResolutionError
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.config.sources.dict_configuration_source import DictConfigurationSource
from flotilla.config.configuration_source import ConfigurationSource
from flotilla.config.secret_resolver import SecretResolver
from flotilla.config.errors import ConfigurationResolutionError


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

    settings = asyncio.run(loader.load())

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

    settings = asyncio.run(loader.load())

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

    settings = asyncio.run(loader.load())

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
        asyncio.run(loader.load())


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


def test_config_mapping_node_is_fully_resolved():
    config = {
        "llm": {
            "openai": {
                "factory": "llm.openai",
                "model": "gpt-4o-mini",
            }
        },
        "agents": {
            "weather_agent": {
                "factory": "agents.weather_agent",
                "llm": {
                    "$config": "llm.openai",
                },
            }
        },
    }

    config_loader = ConfigLoader(sources=[DictConfigurationSource(config)], secrets=[])
    settings = asyncio.run(config_loader.load())
    resolved = settings.config

    llm_cfg = resolved["agents"]["weather_agent"]["llm"]

    assert isinstance(llm_cfg, dict)
    assert llm_cfg["factory"] == "llm.openai"
    assert llm_cfg["model"] == "gpt-4o-mini"


def test_no_config_tokens_remain_after_load():
    config = {
        "base": {
            "x": 1,
        },
        "derived": {
            "$config": "base",
        },
    }
    config_loader = ConfigLoader(sources=[DictConfigurationSource(config)], secrets=[])
    settings = asyncio.run(config_loader.load())
    resolved = settings.config

    def walk(node):
        if isinstance(node, str):
            assert not node.startswith("$config ")
        elif isinstance(node, dict):
            assert "$config" not in node
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(resolved)


def test_config_inside_component_arguments():
    config = {
        "llm": {
            "openai": {
                "factory": "llm.openai",
                "model": "gpt-4o-mini",
            }
        },
        "agent": {"factory": "agents.weather_agent", "llm": {"$config": "llm.openai"}},
    }

    config_loader = ConfigLoader(sources=[DictConfigurationSource(config)], secrets=[])
    settings = asyncio.run(config_loader.load())
    resolved = settings.config

    agent_cfg = resolved["agent"]

    assert isinstance(agent_cfg["llm"], dict)
    assert agent_cfg["llm"]["factory"] == "llm.openai"


def test_config_resolution_is_recursive():
    config = {
        "base": {
            "a": 1,
        },
        "outer": {
            "inner": {
                "$config": "base",
            }
        },
    }

    config_loader = ConfigLoader(sources=[DictConfigurationSource(config)], secrets=[])
    settings = asyncio.run(config_loader.load())
    resolved = settings.config
    assert resolved["outer"]["inner"]["a"] == 1


def test_unresolved_config_raises_error():
    config = {
        "x": {
            "$config": "does.not.exist",
        }
    }
    config_loader = ConfigLoader(sources=[DictConfigurationSource(config)], secrets=[])

    with pytest.raises(Exception):
        asyncio.run(config_loader.load())


########################################


def test_config_scalar_form_is_invalid():
    config = {"llm": "$config llm.openai"}

    loader = ConfigLoader(sources=[DictConfigurationSource(config)])

    with pytest.raises(ConfigurationResolutionError):
        asyncio.run(loader.load())


def test_secret_scalar_form_is_invalid():
    config = {"api_key": "$secret MY_KEY"}

    loader = ConfigLoader(sources=[DictConfigurationSource(config)])

    with pytest.raises(SecretResolutionError):
        asyncio.run(loader.load())
