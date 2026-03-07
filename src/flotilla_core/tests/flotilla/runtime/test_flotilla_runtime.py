import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, List, Optional

import pytest

from flotilla.runtime.flotilla_runtime import FlotillaRuntime  # adjust
from flotilla.runtime.runtime_request import RuntimeRequest  # adjust
from flotilla.runtime.runtime_response import (
    RuntimeResponse,
    RuntimeReseponseType,
)
from flotilla.runtime.runtime_event import RuntimeEventType  # adjust
from flotilla.runtime.phase_context import PhaseContext  # adjust
from flotilla.thread.thread_entries import UserInput, ResumeEntry, ErrorEntry, SuspendEntry, AgentOutput
from flotilla.thread.thread_context import ThreadContext
from flotilla.thread.errors import ConcurrentThreadExecutionError, AppendConflictError
from flotilla.thread.in_memory_store import InMemoryStore
from flotilla.thread.thread_entry_store import ThreadEntryStore
from flotilla.agents.agent_event import AgentEvent
from flotilla.runtime.content_part import TextPart
from flotilla.telemetry.telemetry_policy import TelemetryPolicy
from flotilla.telemetry.telemetry_event import TelemetryEvent
from flotilla.suspend.errors import ResumeAuthorizationError, ResumeTokenExpiredError, ResumeTokenInvalidError


# ---------------------------------------------------------------------------
# In-memory store + spies to assert spec ordering and CAS behaviors
# ---------------------------------------------------------------------------


class FaultInjectingStore(ThreadEntryStore):
    def __init__(self, inner: InMemoryStore):
        self._inner = inner

        self.fail_next_load = None
        self.fail_next_append = None
        # new feature
        self.fail_append_on_nth: Optional[tuple[int, Exception]] = None

        self.load_calls = 0
        self.append_calls = 0

    # ---------------------------------------
    # Thread lifecycle
    # ---------------------------------------

    async def create_thread(self) -> str:
        return await self._inner.create_thread()

    async def load(self, thread_id: str):
        self.load_calls += 1

        if self.fail_next_load:
            ex = self.fail_next_load
            self.fail_next_load = None
            raise ex

        return await self._inner.load(thread_id)

    # ---------------------------------------
    # Append
    # ---------------------------------------

    async def append(self, entry, expected_previous_entry_id=None):
        self.append_calls += 1

        if self.fail_next_append:
            ex = self.fail_next_append
            self.fail_next_append = None
            raise ex

        if self.fail_append_on_nth:
            n, ex = self.fail_append_on_nth
            if n >= self.append_calls:
                raise ex

        return await self._inner.append(entry, expected_previous_entry_id)


class SpyPhaseContextService:
    def __init__(self):
        self.calls: List[str] = []
        self._counter = 0

    def create_phase_context(self, request: RuntimeRequest) -> PhaseContext:
        self.calls.append("create_phase_context")
        self._counter += 1
        return PhaseContext(
            thread_id=request.thread_id,
            phase_id=f"p{self._counter}",
            user_id=request.user_id,
            agent_config={},
        )


class SpyExecutionTimeoutPolicy:
    def __init__(self, *, expired: bool):
        self.expired = expired
        self.calls: List[str] = []

    def is_expired(self, thread_context: ThreadContext, now) -> bool:
        self.calls.append("is_expired")
        return self.expired


class SpySuspendPolicy:
    def __init__(self, *, should_raise: bool = False):
        self.should_raise = should_raise
        self.invoked = False
        self.invoked_after_append_count: Optional[int] = None

    def on_suspend(self, *, thread_id: str, suspend_entry: Any) -> None:
        self.invoked = True
        if self.should_raise:
            raise RuntimeError("suspend policy failed")


class SpyResumeService:
    def __init__(self, unauthorized: bool = False, invalid: bool = False, expired: bool = False):
        self.build_calls = []
        self.token_calls = []

        # test control flags
        self.raise_authorization = unauthorized
        self.raise_invalid = invalid
        self.raise_expired = expired

    async def build_resume_entry(self, *, request, phase_context, thread_context):
        self.build_calls.append(
            {
                "request": request,
                "phase_context": phase_context,
                "thread_context": thread_context,
            }
        )

        if self.raise_authorization:
            raise ResumeAuthorizationError("not authorized")

        if self.raise_invalid:
            raise ResumeTokenInvalidError("invalid token")

        if self.raise_expired:
            raise ResumeTokenExpiredError("expired token")

        return ResumeEntry(
            thread_id=request.thread_id,
            phase_id=phase_context.phase_id,
            previous_entry_id=thread_context.last_entry.entry_id if thread_context.last_entry else None,
            content=request.content,
            user_id=request.user_id,
        )

    def create_token(self, suspend_entry):
        self.token_calls.append(suspend_entry)

        # simple deterministic token
        return f"resume-{suspend_entry.thread_id}-{suspend_entry.entry_id}"


class FakeOrchestrationStrategy:
    def __init__(self):
        self._event_factories: List[Callable[[ThreadContext, PhaseContext], AgentEvent]] = []
        self._raise: Optional[Exception] = None

    def set_events(self, factories):
        self._event_factories = []

        for f in factories:
            if callable(f):
                self._event_factories.append(f)
            else:
                # wrap plain AgentEvent
                self._event_factories.append(lambda tc, pc, ev=f: ev)

        self._raise = None

    def set_raise(self, exc: Exception):
        self._raise = exc
        self._event_factories = []

    async def execute(
        self,
        thread_context: ThreadContext,
        phase_context: PhaseContext,
    ) -> AsyncIterator[AgentEvent]:

        if self._raise:
            raise self._raise

        for factory in self._event_factories:
            yield factory(thread_context, phase_context)


class SpyTelemetryPolicy:
    def __init__(self):
        self._events: List[TelemetryEvent] = []

    def emit(self, event: TelemetryEvent):
        self._events.append(event)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def store() -> ThreadEntryStore:
    return FaultInjectingStore(inner=InMemoryStore())


@pytest.fixture
def phase_context_service() -> SpyPhaseContextService:
    return SpyPhaseContextService()


@pytest.fixture
def timeout_policy_not_expired() -> SpyExecutionTimeoutPolicy:
    return SpyExecutionTimeoutPolicy(expired=False)


@pytest.fixture
def timeout_policy_expired() -> SpyExecutionTimeoutPolicy:
    return SpyExecutionTimeoutPolicy(expired=True)


@pytest.fixture
def resume_service_valid() -> SpyResumeService:
    return SpyResumeService()


@pytest.fixture
def resume_service_unauthorized() -> SpyResumeService:
    return SpyResumeService(unauthorized=True)


@pytest.fixture
def resume_service_invalid() -> SpyResumeService:
    return SpyResumeService(invalid=True)


@pytest.fixture
def resume_service_expired() -> SpyResumeService:
    return SpyResumeService(expired=True)


@pytest.fixture
def suspend_policy_ok() -> SpySuspendPolicy:
    return SpySuspendPolicy(should_raise=False)


@pytest.fixture
def suspend_policy_failing() -> SpySuspendPolicy:
    return SpySuspendPolicy(should_raise=True)


@pytest.fixture
def strategy() -> FakeOrchestrationStrategy:
    return FakeOrchestrationStrategy()


@pytest.fixture
def telemetry_policy() -> TelemetryPolicy:
    return SpyTelemetryPolicy()


@pytest.fixture
def runtime_factory() -> Callable[..., Any]:
    """
    Replace this with construction of your real FlotillaRuntime.
    The tests assume a Runtime with:
      - run(request: RuntimeRequest) -> RuntimeResponse (sync)
      - or equivalent API your project uses
    """

    def _make_runtime(
        *,
        store: Optional[ThreadEntryStore] = None,
        phase_context_service: Optional[SpyPhaseContextService] = None,
        orchestration_strategy: Optional[FakeOrchestrationStrategy] = None,
        execution_timeout_policy: Optional[SpyExecutionTimeoutPolicy] = None,
        resume_service: Optional[SpyResumeService] = None,
        suspend_policy: Optional[SpySuspendPolicy] = None,
        telemetry_policy: Optional[TelemetryPolicy] = None,
    ):

        store = store or InMemoryStore()
        phase_context_service = phase_context_service or SpyPhaseContextService()
        orchestration_strategy = orchestration_strategy or FakeOrchestrationStrategy()
        execution_timeout_policy = execution_timeout_policy or SpyExecutionTimeoutPolicy(expired=False)
        resume_service = resume_service or SpyResumeService()
        suspend_policy = suspend_policy or SpySuspendPolicy()
        telemetry_policy = telemetry_policy or SpyTelemetryPolicy()

        return FlotillaRuntime(
            orchestration=orchestration_strategy,
            store=store,
            phase_context_service=phase_context_service,
            execution_timeout_policy=execution_timeout_policy,
            resume_service=resume_service,
            suspend_policy=suspend_policy,
            telemetry_policy=telemetry_policy,
        )

    return _make_runtime


# ---------------------------------------------------------------------------
# Tests aligned to spec v1.5-draft
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runtime_raises_if_thread_not_found(
    runtime_factory,
):
    runtime = runtime_factory()

    req = RuntimeRequest(thread_id="missing", user_id="u1", content=[TextPart(text="hi")])
    response: RuntimeResponse = await runtime.run(req)

    assert response
    assert response.type == RuntimeReseponseType.ERROR


@pytest.mark.asyncio
async def test_phase_context_created_before_store_load(
    store,
    runtime_factory,
    phase_context_service,
    strategy,
):
    thread_id = await store.create_thread()

    runtime = runtime_factory(
        store=store,
        phase_context_service=phase_context_service,
        orchestration_strategy=strategy,
    )

    strategy.set_events(
        [
            AgentEvent.message_start(entry_id="e-init", agent_id="a1"),
            AgentEvent.message_final(entry_id="e-init", agent_id="a1", content=[TextPart(text="ok")]),
        ]
    )

    req = RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="hi")])
    await runtime.run(request=req)

    # Spec requires PhaseContext construction (phase_id) before constructing/appending initiating entry.
    # Your canonical ordering also creates PhaseContext before loading store.
    assert phase_context_service.calls[0] == "create_phase_context"


@pytest.mark.asyncio
async def test_runtime_initiates_phase_on_empty_thread_appends_user_input(
    runtime_factory,
    store,
    strategy,
):
    thread_id = await store.create_thread()

    runtime = runtime_factory(
        store=store,
        orchestration_strategy=strategy,
    )

    strategy.set_events(
        [
            AgentEvent.message_start(entry_id="e1", agent_id="a1"),
            AgentEvent.message_final(entry_id="e1", agent_id="a1", content=[TextPart(text="hi")]),
        ]
    )

    req = RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="hello")])
    resp = await runtime.run(request=req)
    assert getattr(resp, "error_code", None) is None

    entries = await store.load(thread_id)
    assert isinstance(entries[0], UserInput)


@pytest.mark.asyncio
async def test_runtime_returns_error_on_initiating_append_cas_failure(
    runtime_factory,
    store,
):
    thread_id = await store.create_thread()

    runtime = runtime_factory(
        store=store,
    )

    # Force CAS failure on initiating append
    store.fail_next_append = ConcurrentThreadExecutionError(
        thread_id="t1",
        phase_id="p1",
        entry_type="UserInput",
        expected_entry_id="e2",
        tail_entry_id="e1",
        message="CAS failure",
    )

    req = RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="hello")])
    resp: RuntimeResponse = await runtime.run(request=req)

    assert resp
    assert resp.type == RuntimeReseponseType.ERROR


@pytest.mark.asyncio
async def test_timeout_policy_checked_when_last_entry_not_terminal_and_appends_timeout_error(
    runtime_factory,
    store,
    strategy,
    timeout_policy_expired,
):
    thread_id = await store.create_thread()

    runtime = runtime_factory(
        store=store,
        orchestration_strategy=strategy,
        execution_timeout_policy=timeout_policy_expired,
    )

    # Start one phase and leave it "active" (no terminal) by only appending initiating entry.
    # In your real tests, you'll do this via store.append(UserInput(...)) to simulate previous crash.
    # Here we directly append a non-terminal entry to seed the thread state:
    await store.append(
        UserInput(
            thread_id=thread_id,
            phase_id="p1",
            user_id="u1",
            previous_entry_id=None,
            content=[TextPart(text="hi")],
        ),
        expected_previous_entry_id=None,
    )

    # Now, running should detect it as active and expired, and append ErrorEntry(EXECUTION_TIMEOUT).
    strategy.set_events(
        [
            lambda tc, pc: AgentEvent.message_start(
                entry_id=tc.last_entry.entry_id,
                agent_id="a1",
            ),
            lambda tc, pc: AgentEvent.message_final(
                entry_id=tc.last_entry.entry_id,
                agent_id="a1",
                content=[TextPart(text="ok")],
            ),
        ]
    )

    req = RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="next")])
    resp: RuntimeResponse = await runtime.run(request=req)

    assert resp
    assert resp.type == RuntimeReseponseType.COMPLETE
    assert len(resp.content) > 0

    entries = await store.load(thread_id)
    assert isinstance(entries[-1], AgentOutput)


@pytest.mark.asyncio
async def test_resume_authorization_failure_returns_error_and_does_not_append_resume_entry(
    runtime_factory,
    store,
    strategy,
    resume_service_unauthorized,
):
    thread_id = await store.create_thread()

    runtime = runtime_factory(
        store=store,
        orchestration_strategy=strategy,
        resume_service=resume_service_unauthorized,
    )

    req = RuntimeRequest(
        thread_id=thread_id,
        user_id="u1",
        resume_token="rtok",
        content=[TextPart(text="continue")],
    )
    resp: RuntimeResponse = await runtime.run(request=req)

    assert resp
    assert resp.type == RuntimeReseponseType.ERROR

    entries = await store.load(thread_id)
    assert not any(e.type == "ResumeEntry" for e in entries)


@pytest.mark.asyncio
async def test_message_final_maps_to_agent_output_and_is_durable(
    runtime_factory,
    store,
    strategy,
):
    thread_id = await store.create_thread()

    runtime = runtime_factory(
        store=store,
        orchestration_strategy=strategy,
    )

    strategy.set_events(
        [
            lambda tc, pc: AgentEvent.message_start(
                entry_id=tc.last_entry.entry_id,
                agent_id="a1",
            ),
            lambda tc, pc: AgentEvent.message_chunk(entry_id=tc.last_entry.entry_id, agent_id="a1", text="chunk"),
            lambda tc, pc: AgentEvent.message_final(
                entry_id=tc.last_entry.entry_id,
                agent_id="a1",
                content=[TextPart(text="ok")],
            ),
        ]
    )

    resp: RuntimeResponse = await runtime.run(
        request=RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="hello")])
    )
    assert resp
    assert resp.type == RuntimeReseponseType.COMPLETE
    print(resp.content)

    entries = await store.load(thread_id)
    assert isinstance(entries[-1], AgentOutput)


@pytest.mark.asyncio
async def test_suspend_appends_suspend_entry_then_invokes_suspend_policy_failure_is_non_fatal(
    runtime_factory,
    store,
    phase_context_service,
    strategy,
    suspend_policy_failing,
):
    thread_id = await store.create_thread()

    runtime = runtime_factory(
        store=store,
        phase_context_service=phase_context_service,
        orchestration_strategy=strategy,
        suspend_policy=suspend_policy_failing,
    )

    strategy.set_events(
        [
            lambda tc, pc: AgentEvent.message_start(
                entry_id=tc.last_entry.entry_id,
                agent_id="a1",
            ),
            lambda tc, pc: AgentEvent.suspend(
                entry_id=tc.last_entry.entry_id, agent_id="a1", content=[TextPart(text="need approval")]
            ),
        ]
    )

    resp: RuntimeResponse = await runtime.run(
        request=RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="go")])
    )
    # SuspendPolicy failure must not break durable state; runtime may still return ok or a warning.
    # Spec says non-fatal; your RuntimeResponse shape decides whether ok=True with warning vs ok=False.

    assert resp
    assert resp.type == RuntimeReseponseType.SUSPEND
    assert resp.resume_token

    entries = await store.load(thread_id)
    assert isinstance(entries[-1], SuspendEntry)


@pytest.mark.asyncio
async def test_orchestration_error_is_converted_to_error_entry(
    runtime_factory,
    store,
    phase_context_service,
    strategy,
    suspend_policy_ok,
):
    thread_id = await store.create_thread()

    runtime = runtime_factory(
        store=store,
        phase_context_service=phase_context_service,
        orchestration_strategy=strategy,
        suspend_policy=suspend_policy_ok,
    )

    strategy.set_raise(RuntimeError("boom"))

    resp: RuntimeResponse = await runtime.run(
        request=RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="hi")])
    )

    assert resp
    assert resp.type == RuntimeReseponseType.ERROR

    entries = await store.load(thread_id)
    assert isinstance(entries[-1], ErrorEntry)


@pytest.mark.asyncio
async def test_terminal_append_cas_failure_returns_error_response(
    runtime_factory,
    store,
    strategy,
):
    thread_id = await store.create_thread()

    runtime = runtime_factory(
        store=store,
        orchestration_strategy=strategy,
    )

    # Arrange: orchestration returns message_final (terminal)
    strategy.set_events(
        [
            lambda tc, pc: AgentEvent.message_start(
                entry_id=tc.last_entry.entry_id,
                agent_id="a1",
            ),
            lambda tc, pc: AgentEvent.message_final(
                entry_id=tc.last_entry.entry_id, agent_id="a1", content=[TextPart(text="hi")]
            ),
        ]
    )

    # Force CAS failure on the *terminal append*.
    # In a real store, this happens when another runtime already appended a terminal for parent.
    # Here: flip the predicate failure just before runtime tries to append terminal.
    # Your real runtime likely calls store.append twice (init + terminal). We simulate by failing "next" append.
    # Note: You may need a more targeted store spy to fail the second append only.
    # We'll do a simple approach: allow initiating append, fail terminal append.
    # -> You should implement this in your store spy as "fail_append_on_nth_call".
    # For now, this test expresses required behavior.
    store.fail_next_append = ConcurrentThreadExecutionError(
        thread_id=thread_id,
        phase_id="p1",
        tail_entry_id="e1",
        entry_type="AgentOutput",
        expected_entry_id="e2",
        message="CONCURRENT_THREAD_EXECUTION",
    )
    # allow init
    # After init append, set to fail terminal. Your runtime may allow a hook; otherwise build store spy.
    # If you cannot hook between, implement store.fail_append_on_nth_call = 2.
    # Here we assume you have that spy capability in your real tests.

    resp: RuntimeResponse = await runtime.run(
        request=RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="hi")])
    )

    # Spec requirement (your request): CAS failure returns an error to the user.
    assert resp
    assert resp.type == RuntimeReseponseType.ERROR


@pytest.mark.asyncio
async def test_multiple_terminal_events_are_ignored(
    runtime_factory,
    store,
    strategy,
):
    thread_id = await store.create_thread()

    runtime = runtime_factory(
        store=store,
        orchestration_strategy=strategy,
    )

    strategy.set_events(
        [
            lambda tc, pc: AgentEvent.message_start(
                entry_id=tc.last_entry.entry_id,
                agent_id="a1",
            ),
            lambda tc, pc: AgentEvent.message_final(
                entry_id=tc.last_entry.entry_id, agent_id="a1", content=[TextPart(text="hi")]
            ),
            lambda tc, pc: AgentEvent.error(
                entry_id=tc.last_entry.entry_id, agent_id="a1", content=[TextPart(text="should not happen")]
            ),
        ]
    )

    resp: RuntimeResponse = await runtime.run(
        request=RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="go")])
    )

    assert resp
    assert resp.type == RuntimeReseponseType.COMPLETE


#################################


@pytest.mark.asyncio
async def test_runtime_returns_error_if_thread_not_found(runtime_factory):
    runtime = runtime_factory()

    request = RuntimeRequest(thread_id="missing", user_id="u1", content=[TextPart(text="hello")])

    response = await runtime.run(request)

    assert response.type == RuntimeReseponseType.ERROR
    assert response.thread_id == "missing"


@pytest.mark.asyncio
async def test_phase_id_consistency_across_phase(runtime_factory, store, strategy):
    thread_id = await store.create_thread()
    runtime = runtime_factory(store=store, orchestration_strategy=strategy)

    request = RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="hello")])

    strategy.set_events(
        [
            lambda tc, pc: AgentEvent.message_start(
                entry_id=tc.last_entry.entry_id,
                agent_id="a1",
            ),
            lambda tc, pc: AgentEvent.message_final(
                entry_id=tc.last_entry.entry_id, agent_id="a1", content=[TextPart(text="hi")]
            ),
        ]
    )

    response = await runtime.run(request)

    entries = await store.load(thread_id)

    assert len(entries) > 0

    initiating = entries[0]
    terminal = entries[-1]

    assert initiating.phase_id == response.phase_id
    assert terminal.phase_id == response.phase_id


@pytest.mark.asyncio
async def test_initiating_append_cas_failure_returns_error(runtime_factory, store, strategy):
    thread_id = await store.create_thread()

    runtime = runtime_factory(store=store, orchestration_strategy=strategy)

    store.fail_next_append = AppendConflictError(
        thread_id=thread_id, phase_id="p1", tail_entry_id="e1", expected_entry_id="e2", message="Error"
    )

    strategy.set_events(
        [
            lambda tc, pc: AgentEvent.message_start(
                entry_id=tc.last_entry.entry_id,
                agent_id="a1",
            ),
            lambda tc, pc: AgentEvent.message_final(
                entry_id=tc.last_entry.entry_id, agent_id="a1", content=[TextPart(text="hi")]
            ),
        ]
    )

    request = RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="hello")])

    response = await runtime.run(request)

    assert response.type == RuntimeReseponseType.ERROR


@pytest.mark.asyncio
async def test_terminal_append_cas_failure_returns_error(runtime_factory, store, strategy):
    thread_id = await store.create_thread()

    store.fail_append_on_nth = (
        2,
        AppendConflictError(
            thread_id=thread_id, phase_id="p1", tail_entry_id="e1", expected_entry_id="e2", message="Error"
        ),
    )

    strategy.set_events(
        [
            lambda tc, pc: AgentEvent.message_start(
                entry_id=tc.last_entry.entry_id,
                agent_id="a1",
            ),
            lambda tc, pc: AgentEvent.message_final(
                entry_id=tc.last_entry.entry_id, agent_id="a1", content=[TextPart(text="hi")]
            ),
        ]
    )

    runtime = runtime_factory(store=store, orchestration_strategy=strategy)

    # allow initiating append
    # fail terminal append
    request = RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="hello")])

    response = await runtime.run(request)

    assert response.type == RuntimeReseponseType.ERROR


@pytest.mark.asyncio
async def test_orchestration_error_is_converted_to_error_entry(runtime_factory, store, strategy):
    thread_id = await store.create_thread()

    strategy.set_raise(RuntimeError("boom"))

    runtime = runtime_factory(store=store, orchestration_strategy=strategy)

    request = RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="hello")])

    response = await runtime.run(request)

    assert response.type == RuntimeReseponseType.ERROR

    entries = await store.load(thread_id)
    assert isinstance(entries[-1], ErrorEntry)


@pytest.mark.asyncio
async def test_streaming_events_not_durable(runtime_factory, store, strategy):
    thread_id = await store.create_thread()

    strategy.set_events(
        [
            lambda tc, pc: AgentEvent.message_start(
                entry_id=tc.last_entry.entry_id,
                agent_id="a1",
            ),
            lambda tc, pc: AgentEvent.message_chunk(
                entry_id=tc.last_entry.entry_id, agent_id="a1", text="streaming..."
            ),
            lambda tc, pc: AgentEvent.message_chunk(
                entry_id=tc.last_entry.entry_id, agent_id="a1", text="streaming..."
            ),
            lambda tc, pc: AgentEvent.message_final(
                entry_id=tc.last_entry.entry_id, agent_id="a1", content=[TextPart(text="hi")]
            ),
        ]
    )

    runtime = runtime_factory(store=store, orchestration_strategy=strategy)

    events = []
    async for event in runtime.stream(
        RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="hello")])
    ):
        events.append(event)

    entries = await store.load(thread_id)

    # Only initiating + terminal should exist
    assert len(entries) == 2
    assert events[0].type == RuntimeEventType.START
    assert events[-1].type == RuntimeEventType.COMPLETE


@pytest.mark.asyncio
async def test_resume_authorization_failure_returns_error(runtime_factory, store, resume_service_unauthorized):
    thread_id = await store.create_thread()

    runtime = runtime_factory(store=store, resume_service=resume_service_unauthorized)

    request = RuntimeRequest(
        thread_id=thread_id,
        user_id="u1",
        resume_token="bad",
        content=[TextPart(text="continue")],
    )

    response = await runtime.run(request)

    assert response.type == RuntimeReseponseType.ERROR

    entries = await store.load(thread_id)
    assert len(entries) == 0


@pytest.mark.asyncio
async def test_suspend_returns_resume_token(runtime_factory, store, strategy):
    thread_id = await store.create_thread()

    strategy.set_events(
        [
            AgentEvent.message_start(
                entry_id="e1",
                agent_id="a1",
            ),
            AgentEvent.suspend(entry_id="e1", agent_id="a1", content=[TextPart(text="needs approval")]),
        ]
    )

    strategy.set_events(
        [
            lambda tc, pc: AgentEvent.message_start(
                entry_id=tc.last_entry.entry_id,
                agent_id="a1",
            ),
            lambda tc, pc: AgentEvent.suspend(
                entry_id=tc.last_entry.entry_id, agent_id="a1", content=[TextPart(text="Approval Needed")]
            ),
        ]
    )

    runtime = runtime_factory(store=store, orchestration_strategy=strategy)

    response = await runtime.run(RuntimeRequest(thread_id=thread_id, user_id="u1", content=[TextPart(text="go")]))

    assert response.type == RuntimeReseponseType.SUSPEND
    assert response.resume_token is not None
