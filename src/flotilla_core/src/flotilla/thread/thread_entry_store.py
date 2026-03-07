from abc import ABC
from flotilla.thread.thread_entries import ThreadEntry


class ThreadEntryStore(ABC):

    async def create_thread(self) -> str: ...

    async def load(self, thread_id: str) -> list[ThreadEntry]: ...

    async def append(
        self,
        entry: ThreadEntry,
        expected_previous_entry_id: str | None = None,
    ) -> None: ...
