# tests/runtime/conftest.py

import pytest
from datetime import datetime, timezone
from typing import List, Optional

# --- In-Memory Store (Spec-Compliant) ---


class InMemoryThreadEntryStore:
    def __init__(self):
        self._threads = {}
        self._entry_counter = 0

    async def create_thread(self) -> str:
        thread_id = f"thread-{len(self._threads)+1}"
        self._threads[thread_id] = []
        return thread_id

    async def load(self, thread_id: str):
        if thread_id not in self._threads:
            raise RuntimeError("THREAD_NOT_FOUND")
        return list(self._threads[thread_id])

    async def append(
        self,
        entry,
        expected_last_entry_id: Optional[str] = None,
        require_no_terminal_for_parent: Optional[str] = None,
    ):
        if entry.thread_id not in self._threads:
            raise RuntimeError("THREAD_NOT_FOUND")

        entries = self._threads[entry.thread_id]

        # expected_last_entry_id predicate
        if expected_last_entry_id is None:
            if entries:
                return None
        else:
            if not entries or entries[-1].entry_id != expected_last_entry_id:
                return None

        # require_no_terminal_for_parent predicate
        if require_no_terminal_for_parent:
            for e in entries:
                if getattr(
                    e, "parent_entry_id", None
                ) == require_no_terminal_for_parent and e.type in {
                    "AgentOutput",
                    "SuspendEntry",
                    "ErrorEntry",
                }:
                    return None

        self._entry_counter += 1
        entry.entry_id = f"entry-{self._entry_counter}"
        entry.created_at = datetime.now(timezone.utc)
        entries.append(entry)
        return entry.entry_id


@pytest.mark.asyncio
async def test_runtime_raises_if_thread_not_found(runtime):
    with pytest.raises(RuntimeError):
        await runtime.run(thread_id="missing", request=...)


@pytest.mark.asyncio
async def test_runtime_initiates_phase_on_empty_thread(runtime, store):
    thread_id = await store.create_thread()

    await runtime.run(thread_id=thread_id, request=...)

    entries = await store.load(thread_id)
    assert entries[0].type == "UserInput"


@pytest.mark.asyncio
async def test_runtime_rejects_on_cas_failure(runtime, store):
    thread_id = await store.create_thread()

    # simulate concurrent mutation
    await store.append(fake_user_input(thread_id))

    response = await runtime.run(thread_id=thread_id, request=...)

    assert response.error_code == "CONCURRENT_EXECUTION_PHASE_NOT_ALLOWED"


@pytest.mark.asyncio
async def test_runtime_reloads_after_append(runtime, store_spy):
    thread_id = await store_spy.create_thread()

    await runtime.run(thread_id=thread_id, request=...)

    assert store_spy.load_call_count >= 2


@pytest.mark.asyncio
async def test_message_final_maps_to_agent_output(runtime, strategy, store):
    strategy.set_events(
        [
            AgentEvent.message_start(entry_id="x"),
            AgentEvent.message_final(entry_id="x", content=[TextPart("hi")]),
        ]
    )

    await runtime.run(...)

    entries = await store.load(...)
    assert any(e.type == "AgentOutput" for e in entries)


@pytest.mark.asyncio
async def test_multiple_terminal_events_fail(runtime, strategy):
    strategy.set_events(
        [
            AgentEvent.message_start(...),
            AgentEvent.message_final(...),
            AgentEvent.error(...),
        ]
    )

    with pytest.raises(RuntimeError):
        await runtime.run(...)


@pytest.mark.asyncio
async def test_runtime_appends_timeout_error_when_expired(runtime, timeout_policy_true):
    await runtime.run(...)

    entries = await store.load(...)
    assert entries[-1].type == "ErrorEntry"
    assert entries[-1].error_code == "EXECUTION_TIMEOUT"

@pytest.mark.asyncio
async def test_suspend_policy_invoked_after_durable_append(runtime, suspend_policy_spy):
    strategy.set_events([... suspend ...])

    await runtime.run(...)

    assert suspend_policy_spy.invoked
    assert suspend_policy_spy.invoked_after_store_append

@pytest.mark.asyncio
async def test_suspend_policy_failure_is_non_fatal(runtime, failing_suspend_policy):
    await runtime.run(...)

    # thread must still be suspended
    entries = await store.load(...)
    assert entries[-1].type == "SuspendEntry"

@pytest.mark.asyncio
async def test_telemetry_failure_does_not_break_runtime(runtime, failing_telemetry):
    await runtime.run(...)

    entries = await store.load(...)
    assert entries  # execution completed

@pytest.mark.asyncio
async def test_runtime_rejects_when_thread_closed(runtime, store):
    # append ClosedEntry manually
    with pytest.raises(RuntimeError):
        await runtime.run(...)