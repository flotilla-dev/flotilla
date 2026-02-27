from abc import ABC
from flotilla.thread.thread_entries import ThreadEntry


class ThreadEntryStore(ABC):

    async def create_thread(self) -> str: ...

    async def load(self, thread_id: str) -> list[ThreadEntry]: ...

    async def append(
        self,
        entry: ThreadEntry,
        expected_last_entry_id: str | None = None,
        require_no_terminal_for_parent: str | None = None,
    ) -> str | None: ...
