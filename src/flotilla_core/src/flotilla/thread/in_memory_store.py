from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from flotilla.thread.thread_entry_store import ThreadEntryStore
from flotilla.thread.thread_entries import ThreadEntry
from flotilla.thread.errors import (
    AppendConflictError,
    ThreadNotFoundError,
    ConcurrentThreadExecutionError,
)


class InMemoryStore(ThreadEntryStore):
    """
    In-memory implementation of ThreadEntryStore.

    Intended for:
    - Testing
    - Development
    - Deterministic unit tests

    Not intended for production durability.
    """

    def __init__(self) -> None:
        self._threads: Dict[str, List[ThreadEntry]] = {}
        self._lock = asyncio.Lock()

    # ---------------------------------------------------------
    # Thread lifecycle
    # ---------------------------------------------------------

    async def create_thread(self) -> str:
        thread_id = str(uuid4())

        async with self._lock:
            if thread_id in self._threads:
                # Extremely unlikely, but maintain spec guarantee
                raise Exception("Thread already exists")

            self._threads[thread_id] = []

        return thread_id

    async def load(self, thread_id: str) -> List[ThreadEntry]:
        async with self._lock:
            if thread_id not in self._threads:
                raise ThreadNotFoundError(thread_id=thread_id, message=f"Thread {thread_id} not found")

            # Return immutable snapshot copy
            return list(self._threads[thread_id])

    # ---------------------------------------------------------
    # Append
    # ---------------------------------------------------------

    async def append(
        self,
        entry: ThreadEntry,
        expected_previous_entry_id: Optional[str] = None,
    ) -> ThreadEntry:

        async with self._lock:

            # Thread existence check
            if entry.thread_id not in self._threads:
                raise ThreadNotFoundError(
                    thread_id=entry.thread_id,
                    message=f"Thread {entry.thread_id} does not exist",
                )

            thread_entries = self._threads[entry.thread_id]

            # Reject client-supplied entry_id or timestamp
            if entry.entry_id is not None or entry.timestamp is not None:
                raise AppendConflictError(
                    thread_id=entry.thread_id,
                    phase_id=entry.phase_id,
                    message="Client-supplied entry_id or timestamp is not allowed",
                )

            # Empty thread case
            if not thread_entries:
                if expected_previous_entry_id is not None:
                    raise AppendConflictError(
                        thread_id=entry.thread_id,
                        phase_id=entry.phase_id,
                        expected_entry_id=expected_previous_entry_id,
                        message=f"Expected previous entry id must be None for first append, not {expected_previous_entry_id}",
                    )
                if entry.previous_entry_id is not None:
                    raise AppendConflictError(
                        thread_id=entry.thread_id,
                        phase_id=entry.phase_id,
                        tail_entry_id=entry.previous_entry_id,
                        message=f"previous_entry_id must be None for first append, not {entry.previous_entry_id}",
                    )

            # Non-empty thread case
            else:
                current_tail = thread_entries[-1]

                # Validate CAS parameter
                if current_tail.entry_id != expected_previous_entry_id:
                    raise ConcurrentThreadExecutionError(
                        thread_id=entry.thread_id,
                        phase_id=entry.phase_id,
                        tail_entry_id=current_tail.entry_id,
                        expected_entry_id=expected_previous_entry_id,
                        entry_type=type(entry).__name__,
                        message=f"Current tail entry_id {current_tail.entry_id} does not match expected tail entry_id {expected_previous_entry_id}",
                    )

                # Validate linked-list integrity
                if entry.previous_entry_id != current_tail.entry_id:
                    raise AppendConflictError(
                        thread_id=entry.thread_id,
                        phase_id=entry.phase_id,
                        tail_entry_id=current_tail.entry_id,
                        expected_entry_id=entry.previous_entry_id,
                        message="previous_entry_id must match current tail entry_id",
                    )

            # Assign store-controlled identity + timestamp
            new_entry = entry.model_copy(
                update={
                    "entry_id": str(uuid4()),
                    "timestamp": datetime.now(timezone.utc),
                }
            )

            # Persist append
            thread_entries.append(new_entry)

            return True
