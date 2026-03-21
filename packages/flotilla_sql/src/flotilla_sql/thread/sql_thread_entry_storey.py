from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection

from flotilla.thread.thread_entry_store import ThreadEntryStore
from flotilla.thread.thread_entries import ThreadEntry, ThreadEntryFactory
from flotilla.thread.errors import (
    AppendConflictError,
    ThreadNotFoundError,
    ConcurrentThreadExecutionError,
)
from flotilla.runtime.content_part import ContentPartFactory


class SqlThreadEntryStore(ThreadEntryStore):

    def __init__(self, engine: AsyncEngine):
        self._engine = engine

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    async def create_thread(self) -> str:
        thread_id = str(uuid.uuid4())
        now = self._utc_now_naive()

        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO thread (thread_id, created_at)
                    VALUES (:thread_id, :created_at)
                """
                ),
                {"thread_id": thread_id, "created_at": now},
            )

        return thread_id

    async def load(self, thread_id: str) -> List[ThreadEntry]:
        async with self._engine.begin() as conn:

            if not await self._thread_exists(conn, thread_id):
                raise ThreadNotFoundError(f"Thread does not exist: {thread_id}")

            entry_rows = (
                (
                    await conn.execute(
                        text(
                            """
                        SELECT
                            entry_id,
                            thread_id,
                            entry_order,
                            previous_entry_id,
                            created_at,
                            type,
                            actor_type,
                            actor_id,
                            phase_id
                        FROM thread_entry
                        WHERE thread_id = :thread_id
                        ORDER BY entry_order ASC
                    """
                        ),
                        {"thread_id": thread_id},
                    )
                )
                .mappings()
                .all()
            )

            if not entry_rows:
                return []

            entry_ids = [row["entry_id"] for row in entry_rows]

            part_rows = (
                (
                    await conn.execute(
                        text(
                            """
                        SELECT
                            entry_id,
                            part_index,
                            serialized_payload
                        FROM content_part
                        WHERE entry_id = ANY(:entry_ids)
                        ORDER BY entry_id, part_index
                    """
                        ),
                        {"entry_ids": entry_ids},
                    )
                )
                .mappings()
                .all()
            )

        # Build content map
        parts_by_entry: Dict[str, List[Any]] = {eid: [] for eid in entry_ids}
        for row in part_rows:
            part = ContentPartFactory.deserialize_part(row["serialized_payload"])
            parts_by_entry[row["entry_id"]].append(part)

        # Hydrate via factory
        entries: List[ThreadEntry] = []

        for row in entry_rows:
            data = {
                "type": row["type"],
                "thread_id": row["thread_id"],
                "phase_id": row["phase_id"],
                "entry_id": row["entry_id"],
                "previous_entry_id": row["previous_entry_id"],
                "entry_order": row["entry_order"],
                "timestamp": self._ensure_utc(row["created_at"]),
                "actor_type": row["actor_type"],
                "actor_id": row["actor_id"],
                "content": parts_by_entry[row["entry_id"]],
            }

            entries.append(ThreadEntryFactory.deserialize_entry(data))

        return entries

    async def append(
        self,
        entry: ThreadEntry,
        expected_previous_entry_id: Optional[str] = None,
    ) -> ThreadEntry:

        self._validate_append_request(entry)

        async with self._engine.begin() as conn:

            if not await self._thread_exists(conn, entry.thread_id):
                raise ThreadNotFoundError(f"Thread does not exist: {entry.thread_id}")

            current_tail = await self._load_current_tail_for_update(conn, entry.thread_id)

            self._validate_append_predicates(
                entry,
                expected_previous_entry_id,
                current_tail,
            )

            entry_id = str(uuid.uuid4())
            now = self._utc_now_naive()
            entry_order = 0 if current_tail is None else current_tail["entry_order"] + 1

            entry_data = entry.serialize()

            try:
                # Insert entry
                await conn.execute(
                    text(
                        """
                        INSERT INTO thread_entry (
                            entry_id,
                            thread_id,
                            entry_order,
                            previous_entry_id,
                            created_at,
                            type,
                            actor_type,
                            actor_id,
                            phase_id
                        )
                        VALUES (
                            :entry_id,
                            :thread_id,
                            :entry_order,
                            :previous_entry_id,
                            :created_at,
                            :type,
                            :actor_type,
                            :actor_id,
                            :phase_id
                        )
                    """
                    ),
                    {
                        "entry_id": entry_id,
                        "thread_id": entry.thread_id,
                        "entry_order": entry_order,
                        "previous_entry_id": entry.previous_entry_id,
                        "created_at": now,
                        "type": entry_data["type"],
                        "actor_type": entry_data["actor_type"],
                        "actor_id": entry_data["actor_id"],
                        "phase_id": entry_data["phase_id"],
                    },
                )

                # Batch insert content parts
                parts_payload = [
                    {
                        "entry_id": entry_id,
                        "part_index": idx,
                        "part_type": part.type,
                        "serialized_payload": part.serialize(),
                    }
                    for idx, part in enumerate(entry.content)
                ]

                await conn.execute(
                    text(
                        """
                        INSERT INTO content_part (
                            entry_id,
                            part_index,
                            part_type,
                            serialized_payload
                        )
                        VALUES (
                            :entry_id,
                            :part_index,
                            :part_type,
                            :serialized_payload
                        )
                    """
                    ),
                    parts_payload,
                )

            except IntegrityError as exc:
                raise ConcurrentThreadExecutionError(
                    thread_id=entry.thread_id,
                    phase_id=entry.phase_id,
                    entry_type=entry.type,
                    tail_entry_id=entry.previous_entry_id,
                    expected_entry_id=expected_previous_entry_id,
                    message=f"Concurrent append detected for thread {entry.thread_id}",
                ) from exc

            return entry.model_copy(
                update={
                    "entry_id": entry_id,
                    "timestamp": now,
                    "entry_order": entry_order,
                }
            )

    # --------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------

    async def _thread_exists(self, conn: AsyncConnection, thread_id: str) -> bool:
        result = await conn.execute(
            text("SELECT 1 FROM thread WHERE thread_id = :thread_id"),
            {"thread_id": thread_id},
        )
        return result.scalar_one_or_none() is not None

    async def _load_current_tail_for_update(
        self,
        conn: AsyncConnection,
        thread_id: str,
    ) -> Optional[Dict[str, Any]]:
        result = await conn.execute(
            text(
                """
                SELECT entry_id, entry_order
                FROM thread_entry
                WHERE thread_id = :thread_id
                ORDER BY entry_order DESC
                LIMIT 1
                FOR UPDATE
            """
            ),
            {"thread_id": thread_id},
        )
        return result.mappings().one_or_none()

    def _validate_append_request(self, entry: ThreadEntry) -> None:
        if entry.entry_id is not None:
            raise AppendConflictError(
                thread_id=entry.thread_id, phase_id=entry.phase_id, message="Client-supplied entry_id is not allowed"
            )
        if entry.timestamp is not None:
            raise AppendConflictError(
                thread_id=entry.thread_id, phase_id=entry.phase_id, message="Client-supplied timestamp is not allowed"
            )
        if entry.entry_order not in (None, 0):
            raise AppendConflictError(
                thread_id=entry.thread_id, phase_id=entry.phase_id, message="Client-supplied entry_order is not allowed"
            )
        if not entry.content:
            raise AppendConflictError(
                thread_id=entry.thread_id, phase_id=entry.phase_id, message="ThreadEntry.content must not be empty"
            )

    def _validate_append_predicates(
        self,
        entry: ThreadEntry,
        expected_previous_entry_id: Optional[str],
        current_tail: Optional[Dict[str, Any]],
    ) -> None:

        if current_tail is None:
            if expected_previous_entry_id is not None:
                raise AppendConflictError(
                    thread_id=entry.thread_id,
                    phase_id=entry.phase_id,
                    tail_entry_id=None,
                    expected_entry_id=entry.previous_entry_id,
                    message="expected_previous_entry_id must be None",
                )
            if entry.previous_entry_id is not None:
                raise AppendConflictError(
                    thread_id=entry.thread_id,
                    phase_id=entry.phase_id,
                    tail_entry_id=None,
                    expected_entry_id=expected_previous_entry_id,
                    message="previous_entry_id must be None",
                )
            return

        tail_id = current_tail["entry_id"]

        if expected_previous_entry_id != tail_id:
            raise ConcurrentThreadExecutionError(
                thread_id=entry.thread_id,
                phase_id=entry.phase_id,
                tail_entry_id=tail_id,
                expected_entry_id=expected_previous_entry_id,
                entry_type=entry.type,
                message=f"CAS violation, expected tail id {expected_previous_entry_id} does not match actual tail id {tail_id}",
            )

        if entry.previous_entry_id != tail_id:
            raise ConcurrentThreadExecutionError(
                thread_id=entry.thread_id,
                phase_id=entry.phase_id,
                tail_entry_id=tail_id,
                expected_entry_id=expected_previous_entry_id,
                entry_type=entry.type,
                message=f"CAS violation, previous_entry_id {entry.previous_entry_id} does not match actual tail id {tail_id}",
            )

    @staticmethod
    def _utc_now_naive() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _ensure_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
