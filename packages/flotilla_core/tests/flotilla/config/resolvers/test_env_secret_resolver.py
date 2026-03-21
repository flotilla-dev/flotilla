import pytest

from flotilla.config.resolvers.env_secret_resolver import EnvSecretResolver
from flotilla.config.errors import SecretResolutionError


def test_env_secret_resolver_returns_value(monkeypatch):
    monkeypatch.setenv("MY_SECRET", "super-secret")
    resolver = EnvSecretResolver()
    assert resolver.resolve("MY_SECRET") == "super-secret"


def test_env_secret_resolver_returns_none_for_missing_key():
    resolver = EnvSecretResolver()
    assert resolver.resolve("DOES_NOT_EXIST") is None


def test_env_secret_resolver_returns_none_for_empty_key():
    resolver = EnvSecretResolver()
    assert resolver.resolve("") is None


def test_env_secret_resolver_wraps_unexpected_errors(monkeypatch):
    def boom(_):
        raise RuntimeError("kaboom")

    monkeypatch.setattr("os.environ.get", boom)

    resolver = EnvSecretResolver()

    with pytest.raises(SecretResolutionError):
        resolver.resolve("ANY_KEY")
