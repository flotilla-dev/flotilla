from flotilla.thread.in_memory_store import InMemoryStore
from .thread_entry_store_contract import ThreadEntryStoreContract


class TestInMemoryStore(ThreadEntryStoreContract):

    async def create_store(self):
        return InMemoryStore()
