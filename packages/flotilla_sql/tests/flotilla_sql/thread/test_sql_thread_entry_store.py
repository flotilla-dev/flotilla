from flotilla_testing.thread.thread_entry_store_contract import ThreadEntryStoreContract
from flotilla_sql.thread.sql_thread_entry_storey import SqlThreadEntryStore
import pytest


class TestSqlThreadEntryStore(ThreadEntryStoreContract):

    @pytest.fixture(autouse=True)
    def _inject_store(self, engine):
        self._engine = engine

    async def create_store(self):
        return SqlThreadEntryStore(engine=self._engine)
