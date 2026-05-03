from abc import ABC, abstractmethod
from flotilla.thread.thread_entries import ThreadEntry


class ThreadEntryStore(ABC):
    """
    Durable append-only storage boundary for runtime thread state.

    FlotillaRuntime uses this store to create threads, load the canonical
    ordered ThreadEntry log, and append new entries with compare-and-set
    concurrency protection. The loaded entries are converted into ThreadContext,
    which is the runtime's source of truth for execution decisions.

    Implementations MUST preserve the exact order of entries and enforce
    optimistic concurrency through the `expected_previous_entry_id`
    parameter to ensure that only one writer can append the next entry.

    The store provides durable storage primitives only. It does not enforce
    execution rules, resume semantics, timeout behavior, or orchestration
    outcomes; those guarantees belong to FlotillaRuntime.
    """

    @abstractmethod
    async def create_thread(self) -> str:
        """
        Create a new empty thread log and return its thread id.
        """

    @abstractmethod
    async def load(self, thread_id: str) -> list[ThreadEntry]:
        """
        Return the authoritative ordered ThreadEntry snapshot for a thread.
        """

    @abstractmethod
    async def append(
        self,
        entry: ThreadEntry,
        expected_previous_entry_id: str | None = None,
    ) -> ThreadEntry:
        """
        Append an entry if the current tail matches expected_previous_entry_id.

        The store assigns identity, timestamp, and ordering fields. The returned
        ThreadEntry is informative; callers should reload with load() when they
        need authoritative thread state.
        """
