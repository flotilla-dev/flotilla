import pytest

from flotilla.config.secrets import SecretsResolver


class DummySecretsResolver(SecretsResolver):
    def resolve(self, value: str):
        if value == "secret://db_password":
            return "resolved-password"
        return value


def test_secrets_resolver_resolves_secret():
    resolver = DummySecretsResolver()

    result = resolver.resolve("secret://db_password")

    assert result == "resolved-password"


def test_secrets_resolver_passthrough():
    resolver = DummySecretsResolver()

    result = resolver.resolve("plain-text")

    assert result == "plain-text"
