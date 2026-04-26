import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


async def create_postgres_saver(dsn: str, schema: str) -> "AsyncPostgresSaver":
    """
    Expect `dsn` to be a plain psycopg/libpq Postgres DSN such as `postgresql://...`.
    Do not pass a SQLAlchemy async URL like `postgresql+asyncpg://...` to this provider.
    """
    import psycopg
    from psycopg.rows import dict_row
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    conn = await psycopg.AsyncConnection.connect(
        dsn,
        autocommit=True,
        row_factory=dict_row,
    )

    quoted_schema = _quote_identifier(schema)
    async with conn.cursor() as cursor:
        await cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}")
        await cursor.execute(f"SET search_path TO {quoted_schema}")

    saver = AsyncPostgresSaver(conn)
    await saver.setup()
    return saver


def _quote_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid PostgreSQL schema identifier: {value}")

    return f'"{value}"'
