import pytest

from flotilla.config.resolvers.env_secret_resolver import EnvSecretResolver
from flotilla.config.errors import SecretResolutionError


@pytest.mark.asyncio
async def test_env_secret_resolver_returns_value(monkeypatch):
    monkeypatch.setenv("MY_SECRET", "super-secret")
    resolver = EnvSecretResolver()
    assert await resolver.resolve("MY_SECRET") == "super-secret"


@pytest.mark.asyncio
async def test_env_secret_resolver_returns_none_for_missing_key():
    resolver = EnvSecretResolver()
    assert await resolver.resolve("DOES_NOT_EXIST") is None


@pytest.mark.asyncio
async def test_env_secret_resolver_returns_none_for_empty_key():
    resolver = EnvSecretResolver()
    assert await resolver.resolve("") is None


@pytest.mark.asyncio
async def test_env_secret_resolver_wraps_unexpected_errors(monkeypatch):
    def boom(_):
        raise RuntimeError("kaboom")

    monkeypatch.setattr("os.getenv", boom)

    resolver = EnvSecretResolver()

    with pytest.raises(SecretResolutionError):
        await resolver.resolve("ANY_KEY")
