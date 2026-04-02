from flotilla.thread.thread_entry_store import ThreadEntryStore
from flotilla.thread.thread_entries import ThreadEntry
from typing import List


class ThreadService:
    """
    ThreadService provides a minimal application-facing interface for creating
    and reading Flotilla threads. It acts as a thin wrapper around the
    `ThreadEntryStore`, exposing only safe operations needed by applications.

    This service allows callers to create new threads and load the existing
    list of `ThreadEntry` records for a thread. It intentionally does not
    support appending entries.

    All mutations to a thread MUST occur through `FlotillaRuntime`, which
    enforces execution-phase rules and append-only log semantics.
    """

    def __init__(self, store: ThreadEntryStore):
        """
        Constructs a new ThreadService with the required ThreadEntryStore
        """
        self._store: ThreadEntryStore = store

    async def create_thread(self) -> str:
        """
        Creates a new conversation thread in the internal store and returns the ID of the thread.  Call this
        create a thread before calling FlotillaRuntime.run()/FlotillaRuntime.stream()
        """
        return await self._store.create_thread()

    async def load(self, thread_id: str) -> List[ThreadEntry]:
        """
        Returns the current list of ThreadEntry objects that have been appended to the thread log
        """
        return await self._store.load(thread_id=thread_id)
