from abc import ABC
from flotilla.thread.thread_entries import ThreadEntry


class ThreadEntryStore(ABC):
    """
    ThreadEntryStore defines the persistence interface for Flotilla's
    append-only thread log. It is responsible for creating threads,
    loading the ordered list of `ThreadEntry` records for a thread,
    and appending new entries.

    Implementations MUST preserve the exact order of entries and enforce
    optimistic concurrency through the `expected_previous_entry_id`
    parameter to ensure that only one writer can append the next entry.

    ThreadEntryStore provides durable storage primitives only; it does
    not enforce execution rules or thread semantics. Those guarantees are
    the responsibility of `FlotillaRuntime`.
    """

    async def create_thread(self) -> str: ...

    """
    Creates a new thread instnace in the store and returns the new thread ID.  Needs to be called before
    calling FlotillaRuntime
    """

    async def load(self, thread_id: str) -> list[ThreadEntry]: ...

    """
    Retuns a List of ThreadEntry objects that represent the current state of the Thread log
    """

    async def append(
        self,
        entry: ThreadEntry,
        expected_previous_entry_id: str | None = None,
    ) -> None: ...

    """
    Append a new `ThreadEntry` to the thread's append-only log.

    The `expected_previous_entry_id` parameter is used to enforce optimistic
    concurrency. When provided, the store MUST verify that the current tail
    entry of the thread matches this value before appending the new entry.
    If the value does not match the current tail, the append MUST fail.

    Parameters
    ----------
    entry:
        The `ThreadEntry` to append to the thread log.

    expected_previous_entry_id:
        The expected `entry_id` of the current tail entry. Implementations
        MUST treat this as a compare-and-set (CAS) guard. If the current
        tail entry does not match the provided value, the append MUST be
        rejected.

    Raises
    ------
    ThreadNotFoundError
        Raised if the specified thread does not exist.

    ConcurrentThreadExecutionError
        Raised when the CAS check fails because another process appended
        an entry to the thread before this operation completed.

    AppendConflictError
        Raised for other store-level append conflicts or persistence
        failures that prevent the entry from being written.
    """
