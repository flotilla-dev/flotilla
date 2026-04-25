import asyncio
import re
from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING, Any

from langgraph.checkpoint.base import BaseCheckpointSaver

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.base import ChannelVersions, Checkpoint, CheckpointMetadata, CheckpointTuple
    from langgraph.checkpoint.postgres import PostgresSaver


def create_postgres_saver(dsn: str, schema: str) -> "PostgresSaver":
    """
    Expect `dsn` to be a plain psycopg/libpq Postgres DSN such as `postgresql://...`.
    Do not pass a SQLAlchemy async URL like `postgresql+asyncpg://...` to this provider.
    """
    from langgraph.checkpoint.postgres import PostgresSaver
    import psycopg
    from psycopg.rows import dict_row

    conn = psycopg.connect(
        dsn,
        autocommit=True,
        row_factory=dict_row,
    )

    quoted_schema = _quote_identifier(schema)
    with conn.cursor() as cursor:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}")
        cursor.execute(f"SET search_path TO {quoted_schema}")

    saver = PostgresSaver(conn)
    saver.setup()
    return AsyncCompatiblePostgresSaver(saver)


class AsyncCompatiblePostgresSaver(BaseCheckpointSaver):
    """
    Bridge LangGraph's async checkpoint API onto the sync Postgres saver.
    """

    def __init__(self, saver: "PostgresSaver"):
        super().__init__(serde=saver.serde)
        self._saver = saver

    def __getattr__(self, name: str) -> Any:
        return getattr(self._saver, name)

    def get_tuple(self, config: "RunnableConfig") -> "CheckpointTuple | None":
        return self._saver.get_tuple(config)

    def put(
        self,
        config: "RunnableConfig",
        checkpoint: "Checkpoint",
        metadata: "CheckpointMetadata",
        new_versions: "ChannelVersions",
    ) -> "RunnableConfig":
        return self._saver.put(config, checkpoint, metadata, new_versions)

    def put_writes(
        self,
        config: "RunnableConfig",
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self._saver.put_writes(config, writes, task_id, task_path)

    def list(
        self,
        config: "RunnableConfig | None",
        *,
        filter: dict[str, Any] | None = None,
        before: "RunnableConfig | None" = None,
        limit: int | None = None,
    ):
        return self._saver.list(config, filter=filter, before=before, limit=limit)

    async def aget_tuple(self, config: "RunnableConfig") -> "CheckpointTuple | None":
        return await asyncio.to_thread(self._saver.get_tuple, config)

    async def aput(
        self,
        config: "RunnableConfig",
        checkpoint: "Checkpoint",
        metadata: "CheckpointMetadata",
        new_versions: "ChannelVersions",
    ) -> "RunnableConfig":
        return await asyncio.to_thread(self._saver.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: "RunnableConfig",
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        await asyncio.to_thread(self._saver.put_writes, config, writes, task_id, task_path)

    async def alist(
        self,
        config: "RunnableConfig | None",
        *,
        filter: dict[str, Any] | None = None,
        before: "RunnableConfig | None" = None,
        limit: int | None = None,
    ) -> AsyncIterator["CheckpointTuple"]:
        values = await asyncio.to_thread(
            lambda: list(self._saver.list(config, filter=filter, before=before, limit=limit))
        )
        for value in values:
            yield value

    async def adelete_thread(self, thread_id: str) -> None:
        await asyncio.to_thread(self._saver.delete_thread, thread_id)


def _quote_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid PostgreSQL schema identifier: {value}")

    return f'"{value}"'
