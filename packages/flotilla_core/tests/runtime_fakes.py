from typing import Any, AsyncIterator, Callable, List, Optional
from flotilla.thread.thread_context import ThreadContext
from flotilla.runtime.phase_context import PhaseContext  # adjust
from flotilla.telemetry.telemetry_event import TelemetryEvent
from flotilla.suspend.errors import ResumeAuthorizationError, ResumeTokenExpiredError, ResumeTokenInvalidError
from flotilla.thread.thread_entries import ResumeEntry
from flotilla.thread.thread_entry_store import ThreadEntryStore
from flotilla.thread.in_memory_store import InMemoryStore
from flotilla.runtime.runtime_request import RuntimeRequest
from flotilla.agents.agent_event import AgentEvent
from flotilla.runtime.phase_context_service import PhaseContextService
from flotilla.runtime.orchestration_strategy import OrchestrationStrategy
from flotilla.suspend.resume_service import ResumeService
from flotilla.suspend.suspend_service import SuspendService
from flotilla.telemetry.telemetry_service import TelemetryService
from flotilla.timeout.execution_timeout_policy import ExecutionTimeoutPolicy


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


class SpyPhaseContextService(PhaseContextService):
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


class SpyExecutionTimeoutPolicy(ExecutionTimeoutPolicy):
    def __init__(self, *, expired: bool):
        self.expired = expired
        self.calls: List[str] = []

    def is_expired(self, thread_context: ThreadContext, now) -> bool:
        self.calls.append("is_expired")
        return self.expired


class SpySuspendService(SuspendService):
    def __init__(self, *, should_raise: bool = False):
        self.should_raise = should_raise
        self.invoked = False
        self.invoked_after_append_count: Optional[int] = None

    async def handle_suspend(self, thread_context, suspend_entry, resume_token, phase_context) -> None:
        self.invoked = True
        if self.should_raise:
            raise RuntimeError("suspend service failed")


class SpyResumeService(ResumeService):
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
            actor_id=request.user_id,
        )

    def create_token(self, suspend_entry):
        self.token_calls.append(suspend_entry)

        # simple deterministic token
        return f"resume-{suspend_entry.thread_id}-{suspend_entry.entry_id}"


class FakeOrchestrationStrategy(OrchestrationStrategy):
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


class SpyTelemetryService(TelemetryService):
    def __init__(self):
        self._events: List[TelemetryEvent] = []

    def emit(self, event: TelemetryEvent):
        print(f"TelemtetryEvent: {event}")
        self._events.append(event)
