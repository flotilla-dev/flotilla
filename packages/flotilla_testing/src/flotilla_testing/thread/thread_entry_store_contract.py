import pytest
from abc import ABC, abstractmethod
from datetime import datetime
import uuid

from flotilla.thread.thread_entry_store import ThreadEntryStore
from flotilla.thread.thread_context import ThreadContext
from flotilla.thread.thread_entries import UserInput
from flotilla.runtime.content_part import TextPart
from flotilla.thread.errors import (
    AppendConflictError,
    ThreadNotFoundError,
    ConcurrentThreadExecutionError,
)


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
            thread_id=str(uuid.uuid4()),
            phase_id="p1",
            content=[self.make_text("test")],
            actor_id="u1",
        )
        with pytest.raises(ThreadNotFoundError):
            await store.append(entry)

    @pytest.mark.asyncio
    async def test_load_nonexistent_thread_fails(self, store):
        with pytest.raises(ThreadNotFoundError):
            await store.load(str(uuid.uuid4()))

    @pytest.mark.asyncio
    async def test_first_append_requires_none_previous(self, store):
        thread_id = await store.create_thread()

        entry = UserInput(
            thread_id=thread_id,
            phase_id="p1",
            content=[self.make_text("test")],
            actor_id="u1",
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
            actor_id="u1",
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
                actor_id="u1",
                previous_entry_id=None,
            ),
            expected_previous_entry_id=None,
        )

        thread_context = ThreadContext(entries=await store.load(thread_id=thread_id))

        e2 = UserInput(
            thread_id=thread_id,
            phase_id="p2",
            content=[self.make_text("test")],
            actor_id="u1",
            previous_entry_id=thread_context.last_entry.entry_id,
        )

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
                actor_id="u1",
                previous_entry_id=None,
            ),
            expected_previous_entry_id=None,
        )

        bad_entry = UserInput(
            thread_id=thread_id,
            phase_id="p2",
            content=[self.make_text("test")],
            actor_id="u1",
            previous_entry_id="wrong-id",
        )

        thread_context = ThreadContext(entries=await store.load(thread_id=thread_id))

        with pytest.raises(ConcurrentThreadExecutionError):
            await store.append(
                bad_entry,
                expected_previous_entry_id=thread_context.last_entry.entry_id,
            )

    @pytest.mark.asyncio
    async def test_expected_and_entry_previous_must_match(self, store):
        thread_id = await store.create_thread()

        await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p1",
                content=[self.make_text("test")],
                actor_id="u1",
                previous_entry_id=None,
            ),
            expected_previous_entry_id=None,
        )

        entries = await store.load(thread_id)

        entry = UserInput(
            thread_id=thread_id,
            phase_id="p2",
            content=[self.make_text("test")],
            actor_id="u1",
            previous_entry_id=entries[0].entry_id,
        )

        # Structural mismatch → must raise ConcurrentThreadExecutionError
        with pytest.raises(ConcurrentThreadExecutionError):
            await store.append(entry, expected_previous_entry_id=None)

    @pytest.mark.asyncio
    async def test_error_precedence_structural_over_cas(self, store):
        thread_id = await store.create_thread()

        await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p1",
                content=[self.make_text("test")],
                actor_id="u1",
                previous_entry_id=None,
            ),
            expected_previous_entry_id=None,
        )

        entry = UserInput(
            thread_id=thread_id,
            phase_id="p2",
            content=[self.make_text("test")],
            actor_id="u1",
            previous_entry_id="wrong-id",
        )

        with pytest.raises(ConcurrentThreadExecutionError):
            await store.append(entry, expected_previous_entry_id="also-wrong")

    @pytest.mark.asyncio
    async def test_reject_client_supplied_entry_id(self, store):
        thread_id = await store.create_thread()

        entry = UserInput(
            thread_id=thread_id,
            phase_id="p1",
            content=[self.make_text("test")],
            actor_id="u1",
            previous_entry_id=None,
        )

        entry = entry.model_copy(update={"entry_id": "hack"})

        with pytest.raises(AppendConflictError):
            await store.append(entry, expected_previous_entry_id=None)

    @pytest.mark.asyncio
    async def test_reject_client_supplied_timestamp(self, store):
        thread_id = await store.create_thread()

        entry = UserInput(
            thread_id=thread_id,
            phase_id="p1",
            content=[self.make_text("test")],
            actor_id="u1",
            previous_entry_id=None,
        )

        entry = entry.model_copy(update={"timestamp": datetime.utcnow()})

        with pytest.raises(AppendConflictError):
            await store.append(entry, expected_previous_entry_id=None)

    @pytest.mark.asyncio
    async def test_append_returns_realized_entry(self, store):
        thread_id = await store.create_thread()

        entry = UserInput(
            thread_id=thread_id,
            phase_id="p1",
            content=[self.make_text("test")],
            actor_id="u1",
            previous_entry_id=None,
        )

        result = await store.append(entry, expected_previous_entry_id=None)

        assert result.entry_id is not None
        assert result.timestamp is not None

    @pytest.mark.asyncio
    async def test_append_returns_new_instance(self, store):
        thread_id = await store.create_thread()

        entry = UserInput(
            thread_id=thread_id,
            phase_id="p1",
            content=[self.make_text("test")],
            actor_id="u1",
            previous_entry_id=None,
        )

        result = await store.append(entry, expected_previous_entry_id=None)

        assert result is not entry

    @pytest.mark.asyncio
    async def test_load_returns_strict_order(self, store):
        thread_id = await store.create_thread()

        await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p1",
                content=[self.make_text("test")],
                actor_id="u1",
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
                actor_id="u1",
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
                actor_id="u1",
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
                actor_id="u1",
                previous_entry_id=entries[0].entry_id,
            ),
            expected_previous_entry_id=entries[0].entry_id,
        )

        entries = await store.load(thread_id)

        assert entries[1].timestamp >= entries[0].timestamp

    @pytest.mark.asyncio
    async def test_content_parts_preserved(self, store):
        thread_id = await store.create_thread()

        content = [
            self.make_text("a"),
            self.make_text("b"),
            self.make_text("c"),
        ]

        await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p1",
                content=content,
                actor_id="u1",
                previous_entry_id=None,
            ),
            expected_previous_entry_id=None,
        )

        entries = await store.load(thread_id)

        assert [p.text for p in entries[0].content] == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_load_empty_thread_returns_empty_list(self, store):
        thread_id = await store.create_thread()
        entries = await store.load(thread_id)
        assert entries == []

    @pytest.mark.asyncio
    async def test_entry_order_starts_at_zero_and_increments(self, store):
        thread_id = await store.create_thread()

        e1 = await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p1",
                content=[self.make_text("a")],
                actor_id="u1",
                previous_entry_id=None,
            ),
            expected_previous_entry_id=None,
        )

        e2 = await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p2",
                content=[self.make_text("b")],
                actor_id="u1",
                previous_entry_id=e1.entry_id,
            ),
            expected_previous_entry_id=e1.entry_id,
        )

        entries = await store.load(thread_id)

        assert getattr(entries[0], "entry_order") == 0
        assert getattr(entries[1], "entry_order") == 1

    @pytest.mark.asyncio
    async def test_entry_order_is_gapless(self, store):
        thread_id = await store.create_thread()

        prev = None
        for i in range(5):
            entry = await store.append(
                UserInput(
                    thread_id=thread_id,
                    phase_id=f"p{i}",
                    content=[self.make_text(str(i))],
                    actor_id="u1",
                    previous_entry_id=prev,
                ),
                expected_previous_entry_id=prev,
            )
            prev = entry.entry_id

        entries = await store.load(thread_id)

        orders = [getattr(e, "entry_order") for e in entries]

        assert orders == list(range(len(entries)))

    @pytest.mark.asyncio
    async def test_load_returns_entries_sorted_by_entry_order(self, store):
        thread_id = await store.create_thread()

        prev = None
        for i in range(3):
            result = await store.append(
                UserInput(
                    thread_id=thread_id,
                    phase_id=f"p{i}",
                    content=[self.make_text(str(i))],
                    actor_id="u1",
                    previous_entry_id=prev,
                ),
                expected_previous_entry_id=prev,
            )
            prev = result.entry_id

        entries = await store.load(thread_id)

        orders = [getattr(e, "entry_order") for e in entries]

        assert orders == sorted(orders)

    @pytest.mark.asyncio
    async def test_entry_order_is_immutable(self, store):
        thread_id = await store.create_thread()

        entry = await store.append(
            UserInput(
                thread_id=thread_id,
                phase_id="p1",
                content=[self.make_text("x")],
                actor_id="u1",
                previous_entry_id=None,
            ),
            expected_previous_entry_id=None,
        )

        entries = await store.load(thread_id)
        original_order = entries[0].entry_order

        entries_again = await store.load(thread_id)

        assert entries_again[0].entry_order == original_order

    @pytest.mark.asyncio
    async def test_entry_order_unique_per_thread(self, store):
        thread_id = await store.create_thread()

        prev = None
        for i in range(3):
            result = await store.append(
                UserInput(
                    thread_id=thread_id,
                    phase_id=f"p{i}",
                    content=[self.make_text(str(i))],
                    actor_id="u1",
                    previous_entry_id=prev,
                ),
                expected_previous_entry_id=prev,
            )
            prev = result.entry_id

        entries = await store.load(thread_id)

        orders = [e.entry_order for e in entries]

        assert len(orders) == len(set(orders))
