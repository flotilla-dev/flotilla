import pytest
from abc import ABC, abstractmethod
from flotilla.thread.thread_entry_store import ThreadEntryStore
from flotilla.thread.thread_context import ThreadContext
from datetime import datetime
from flotilla.thread.thread_entries import UserInput
from flotilla.runtime.content_part import TextPart
from flotilla.thread.errors import AppendConflictError, ThreadNotFoundError, ConcurrentThreadExecutionError


class ThreadEntryStoreContract(ABC):

    @abstractmethod
    async def create_store(self) -> ThreadEntryStore:
        raise NotImplementedError

    def make_text(self, text: str) -> TextPart:
        return TextPart(text=text)

    @pytest.fixture
    async def store(self) -> ThreadEntryStore:
        return await self.create_store()

    @pytest.mark.asyncio
    async def test_create_thread_returns_unique_id(self, store):
        t1 = await store.create_thread()
        t2 = await store.create_thread()
        assert t1 != t2

    @pytest.mark.asyncio
    async def test_append_fails_if_thread_does_not_exist(self, store):
        entry = UserInput(
            thread_id="nonexistent",
            phase_id="p1",
            content=[self.make_text("test")],
            user_id="u1",
        )
        with pytest.raises(ThreadNotFoundError):
            await store.append(entry)

    @pytest.mark.asyncio
    async def test_first_append_requires_none_previous(self, store):
        thread_id = await store.create_thread()

        entry = UserInput(
            thread_id=thread_id,
            phase_id="p1",
            content=[self.make_text("test")],
            user_id="u1",
            previous_entry_id=None,
        )

        await store.append(entry, expected_previous_entry_id=None)

        thread_context = ThreadContext(entries=await store.load(thread_id=thread_id))

        assert thread_context.last_entry.entry_id is not None
        assert thread_context.last_entry.timestamp is not None

    @pytest.mark.asyncio
    async def test_first_append_rejects_if_expected_previous_not_none(self, store):
        thread_id = await store.create_thread()

        entry = UserInput(
            thread_id=thread_id,
            phase_id="p1",
            content=[self.make_text("test")],
            user_id="u1",
            previous_entry_id=None,
        )

        with pytest.raises(AppendConflictError):
            await store.append(entry, expected_previous_entry_id="bogus")

    @pytest.mark.asyncio
    async def test_cas_enforced_on_append(self, store):
        thread_id = await store.create_thread()

        await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p1",
                content=[self.make_text("test")],
                user_id="u1",
                previous_entry_id=None,
            ),
            expected_previous_entry_id=None,
        )

        thread_context = ThreadContext(entries=await store.load(thread_id=thread_id))

        e2 = UserInput(
            thread_id=thread_id,
            phase_id="p2",
            content=[self.make_text("test")],
            user_id="u1",
            previous_entry_id=thread_context.last_entry.entry_id,
        )

        # simulate stale client
        with pytest.raises(ConcurrentThreadExecutionError):
            await store.append(e2, expected_previous_entry_id="stale-id")

    @pytest.mark.asyncio
    async def test_previous_entry_id_must_match_expected(self, store):
        thread_id = await store.create_thread()

        await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p1",
                content=[self.make_text("test")],
                user_id="u1",
                previous_entry_id=None,
            ),
            expected_previous_entry_id=None,
        )

        bad_entry = UserInput(
            thread_id=thread_id,
            phase_id="p2",
            content=[self.make_text("test")],
            user_id="u1",
            previous_entry_id="wrong-id",
        )

        thread_context = ThreadContext(entries=await store.load(thread_id=thread_id))

        with pytest.raises(AppendConflictError):
            await store.append(bad_entry, expected_previous_entry_id=thread_context.last_entry.entry_id)

    @pytest.mark.asyncio
    async def test_reject_client_supplied_entry_id(self, store):
        thread_id = await store.create_thread()

        entry = UserInput(
            thread_id=thread_id,
            phase_id="p1",
            content=[self.make_text("test")],
            user_id="u1",
            previous_entry_id=None,
        )

        entry = entry.model_copy(update={"entry_id": "hack"})

        with pytest.raises(AppendConflictError):
            await store.append(entry, expected_previous_entry_id=None)

    @pytest.mark.asyncio
    async def test_load_returns_strict_order(self, store):
        thread_id = await store.create_thread()

        await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p1",
                content=[self.make_text("test")],
                user_id="u1",
                previous_entry_id=None,
            ),
            expected_previous_entry_id=None,
        )

        entries = await store.load(thread_id)

        await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p2",
                content=[self.make_text("test")],
                user_id="u1",
                previous_entry_id=entries[0].entry_id,
            ),
            expected_previous_entry_id=entries[0].entry_id,
        )

        entries = await store.load(thread_id)

        assert entries[0].previous_entry_id is None
        assert entries[1].previous_entry_id == entries[0].entry_id

    @pytest.mark.asyncio
    async def test_timestamp_monotonicity(self, store):
        thread_id = await store.create_thread()

        await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p1",
                content=[self.make_text("test")],
                user_id="u1",
                previous_entry_id=None,
            ),
            expected_previous_entry_id=None,
        )

        entries = await store.load(thread_id)

        await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p2",
                content=[self.make_text("test")],
                user_id="u1",
                previous_entry_id=entries[0].entry_id,
            ),
            expected_previous_entry_id=entries[0].entry_id,
        )

        entries = await store.load(thread_id)

        assert entries[1].timestamp >= entries[0].timestamp

    @pytest.mark.asyncio
    async def test_reject_client_supplied_timestamp(self, store):
        thread_id = await store.create_thread()

        entry = UserInput(
            thread_id=thread_id,
            phase_id="p1",
            content=[self.make_text("test")],
            user_id="u1",
            previous_entry_id=None,
        )

        entry = entry.model_copy(update={"timestamp": datetime.utcnow()})

        with pytest.raises(AppendConflictError):
            await store.append(entry, expected_previous_entry_id=None)

    @pytest.mark.asyncio
    async def test_expected_and_entry_previous_must_match(self, store):
        thread_id = await store.create_thread()

        e1 = await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p1",
                content=[self.make_text("test")],
                user_id="u1",
                previous_entry_id=None,
            ),
            expected_previous_entry_id=None,
        )

        entries = await store.load(thread_id)

        entry = UserInput(
            thread_id=thread_id,
            phase_id="p2",
            content=[self.make_text("test")],
            user_id="u1",
            previous_entry_id=entries[0].entry_id,
        )

        with pytest.raises(ConcurrentThreadExecutionError):
            await store.append(entry, expected_previous_entry_id=None)

    @pytest.mark.asyncio
    async def test_load_empty_thread_returns_empty_list(self, store):
        thread_id = await store.create_thread()
        entries = await store.load(thread_id)
        assert entries == []
