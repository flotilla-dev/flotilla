from unittest.mock import MagicMock

from flotilla_sql import async_engine_provider as provider_module


def test_async_engine_provider_passes_async_sqlalchemy_dsn_through(monkeypatch):
    create_async_engine = MagicMock()
    monkeypatch.setattr(provider_module, "create_async_engine", create_async_engine)
    dsn = "postgresql+asyncpg://user:pass@localhost:5432/flotilla_db?options=-csearch_path%3Dtenant"

    provider_module.async_engine_provider(dsn)

    create_async_engine.assert_called_once()
    kwargs = create_async_engine.call_args.kwargs
    assert kwargs["url"] == dsn
