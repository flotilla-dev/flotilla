# flotilla/runtime/flotilla_runtime.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator, Optional, Union

from flotilla.runtime.runtime_request import (
    RuntimeRequest,
)
from flotilla.runtime.runtime_response import (
    RuntimeResponse,
    RuntimeReseponseType,
)
from flotilla.runtime.runtime_event import RuntimeEvent, RuntimeEventType, RuntimeEventFactory

from flotilla.runtime.phase_context import PhaseContext
from flotilla.runtime.phase_context_service import PhaseContextService
from flotilla.runtime.content_part import ContentPart, TextPart

# Thread model / entries
from flotilla.thread.thread_context import ThreadContext, ThreadStatus
from flotilla.thread.thread_entry_store import ThreadEntryStore
from flotilla.thread.errors import (
    AppendConflictError,
    ThreadNotFoundError,
    ConcurrentThreadExecutionError,
)
from flotilla.thread.thread_entries import (
    ThreadEntry,
    UserInput,
    SuspendEntry,
    ErrorEntry,
    ThreadEntryFactory,
)

from flotilla.timeout.execution_timeout_policy import ExecutionTimeoutPolicy
from flotilla.suspend.suspend_policy import SuspendPolicy
from flotilla.suspend.resume_service import ResumeService
from flotilla.suspend.errors import ResumeAuthorizationError, ResumeTokenExpiredError, ResumeTokenInvalidError
from flotilla.runtime.orchestration_strategy import OrchestrationStrategy
from flotilla.telemetry.telemetry_policy import TelemetryPolicy
from flotilla.telemetry.telemetry_event import TelemetryEvent
from flotilla.telemetry.telemetry_types import TelemeryType, TelemetryComponent

# AgentEvent


# =============================================================================
# FlotillaRuntime
# =============================================================================


class FlotillaRuntime:
    """
    Stateless orchestration kernel.

    Implements the behavior contract:
      - Construct PhaseContext before any ThreadEntry is constructed/appended
      - Load ThreadContext, enforce lazy timeout if prior phase active
      - Validate resume (if present) before appending ResumeEntry
      - Append initiating entry via CAS, then durable reload
      - Run OrchestrationStrategy, stream non-terminal events ephemerally
      - Append exactly one terminal entry via CAS, then durable reload
      - Convert orchestration exceptions to durable ErrorEntry
      - CAS failures return RuntimeResponse/RuntimeEvent ERROR
    """

    def __init__(
        self,
        orchestration: OrchestrationStrategy,
        store: ThreadEntryStore,
        phase_context_service: PhaseContextService,
        execution_timeout_policy: ExecutionTimeoutPolicy,
        resume_service: ResumeService,
        suspend_policy: SuspendPolicy,
        telemetry_policy: TelemetryPolicy,
    ):
        self._orchestration = orchestration
        self._store = store
        self._phase_context_service = phase_context_service
        self._timeout_policy = execution_timeout_policy
        self._resume_service = resume_service
        self._suspend_policy = suspend_policy
        self._telemetry_policy = telemetry_policy

    # ------------------------------------------
    # Public API
    # ------------------------------------------

    async def run(self, request: RuntimeRequest) -> RuntimeResponse:
        last_event: Optional[RuntimeEvent] = None

        async for event in self.stream(request):
            last_event = event

            if last_event is None:
                pass
                """
                return RuntimeResponse(
                    type=RuntimeReseponseType.ERROR,
                    thread_id=request.thread_id,
                    phase_id="uknown",
                    correlation_id=request.correlation_id,
                    trace_id=request.trace_id,
                    content=[TextPart("")]
                )
                """

            if last_event.type == RuntimeEventType.ERROR:
                return RuntimeResponse(
                    type=RuntimeReseponseType.ERROR,
                    thread_id=last_event.thread_id,
                    phase_id=last_event.phase_id,
                    correlation_id=last_event.correlation_id,
                    trace_id=last_event.trace_id,
                    content=last_event.content,
                )
            if last_event.type == RuntimeEventType.SUSPEND:
                return RuntimeResponse(
                    type=RuntimeReseponseType.SUSPEND,
                    thread_id=last_event.thread_id,
                    phase_id=last_event.phase_id,
                    correlation_id=last_event.correlation_id,
                    trace_id=last_event.trace_id,
                    content=last_event.content,
                    resume_token=last_event.resume_token,
                )

        return RuntimeResponse(
            type=RuntimeReseponseType.COMPLETE,
            thread_id=last_event.thread_id,
            phase_id=last_event.phase_id,
            correlation_id=last_event.correlation_id,
            trace_id=last_event.trace_id,
            content=last_event.content,
        )

    async def stream(self, request: RuntimeRequest) -> AsyncIterator[RuntimeEvent]:
        #   1.  Receive `RuntimeRequest`.
        #   2.  Construct `PhaseContext` via `PhaseContextService`.
        phase_context: PhaseContext = self._phase_context_service.create_phase_context(request=request)

        #   3.  Load durable thread state (`ThreadEntryStore.load()`).
        result = await self._load_thread_context(request.thread_id, phase_context)

        if isinstance(result, RuntimeEvent):
            yield result
            return

        thread_context = result

        #   4.  If ThreadContext indicates an active running phase:
        if thread_context.status == ThreadStatus.RUNNING:
            event = await self._process_timeout(
                request=request,
                phase_context=phase_context,
                thread_context=thread_context,
            )
            if event:
                yield event
                return

            result = await self._load_thread_context(request.thread_id, phase_context)

            if isinstance(result, RuntimeEvent):
                yield result
                return

            thread_context = result

        # define the ThreadEntry that will be appended
        entry: ThreadEntry = None
        # define previous_entry_id and default to None for first time UserInput caes
        previous_entry_id: str = None
        if thread_context.last_entry:
            previous_entry_id = thread_context.last_entry.entry_id

        #   5.  If `resume_token` is present
        if request.resume_token:
            # attempt to build ResumeEntry from the token
            try:
                entry = await self._resume_service.build_resume_entry(
                    request=request, phase_context=phase_context, thread_context=thread_context
                )
            except ResumeAuthorizationError as ex:
                yield self._generate_runtime_error(
                    phase_context=phase_context,
                    user_message="USER_NOT_AUTHORIZED",
                    telemetry_type=TelemeryType.RESUME_AUTH_FAILURE,
                    telemetry_message="USER_NOT_AUTHORIZED",
                    error=ex,
                )
                return
            except (ResumeTokenInvalidError, ResumeTokenExpiredError) as ex:
                yield self._generate_runtime_error(
                    phase_context=phase_context,
                    user_message="INVALID_RESUME_TOKEN",
                    telemetry_type=TelemeryType.RESUME_INVALID_TOKEN_FAILURE,
                    telemetry_message="INVALID_RESUME_TOKEN",
                    error=ex,
                )
                return
        else:
            #   6.  Construct UserInput:
            entry = UserInput(
                thread_id=request.thread_id,
                phase_id=phase_context.phase_id,
                previous_entry_id=previous_entry_id,
                content=request.content,
                user_id=request.user_id,
            )

        #   7.  Attempt CAS append of start entry.
        event = await self._append_entry(
            entry=entry, expected_previous_entry_id=previous_entry_id, phase_context=phase_context
        )
        if event:
            yield event
            return

        #   8.  Perform durable reload.
        result = await self._load_thread_context(request.thread_id, phase_context)

        if isinstance(result, RuntimeEvent):
            yield result
            return

        thread_context = result

        #   9.  Invoke `OrchestrationStrategy(thread_context, phase_context)`.
        # forward orchestration runtime events
        async for event in self._execute_orchestration(
            thread_context=thread_context,
            phase_context=phase_context,
        ):
            yield event

    # ------------------------------------------
    # Private helpers
    # ------------------------------------------

    async def _load_thread_context(
        self,
        thread_id: str,
        phase_context: PhaseContext,
    ) -> Union[ThreadContext, RuntimeEvent]:

        try:
            entries = await self._store.load(thread_id=thread_id)
            return ThreadContext(entries=entries)

        except ThreadNotFoundError as ex:
            return self._generate_runtime_error(
                phase_context=phase_context,
                user_message="UNKNOWN_THREAD",
                telemetry_type=TelemeryType.RUNTIME_UNKNOWN_THREAD_FAILURE,
                telemetry_message="Thread not found",
                error=ex,
            )

    async def _process_timeout(
        self,
        request: RuntimeRequest,
        phase_context: PhaseContext,
        thread_context: ThreadContext,
    ) -> Optional[RuntimeEvent]:

        expired = self._timeout_policy.is_expired(
            thread_context=thread_context,
            now=self._now(),
        )

        print("expired:", expired, type(expired))

        # thread still running and not expired
        if not expired:
            return self._generate_runtime_error(
                phase_context=phase_context,
                user_message="CONCURRENT_THREAD_EXECUTION",
                telemetry_type=TelemeryType.ACTIVE_THREAD_REJECTED,
                telemetry_message="Thread still running",
            )

        # thread expired -> attempt timeout close
        return await self._append_entry(
            ErrorEntry(
                thread_id=request.thread_id,
                phase_id=thread_context.last_entry.phase_id,
                previous_entry_id=thread_context.last_entry.entry_id,
                content=[TextPart(text="EXECUTION_TIMEOUT")],
                agent_id="SYSTEM",
            ),
            expected_previous_entry_id=thread_context.last_entry.entry_id,
            phase_context=phase_context,
        )

    async def _append_entry(
        self, entry: ThreadEntry, expected_previous_entry_id: str, phase_context: PhaseContext
    ) -> Optional[RuntimeEvent]:
        try:
            await self._store.append(
                entry=entry,
                expected_previous_entry_id=expected_previous_entry_id,
            )
            return None

        except (AppendConflictError, ConcurrentThreadExecutionError) as ex:
            return self._generate_runtime_error(
                phase_context=phase_context,
                user_message="CONCURRENT_THREAD_EXECUTION",
                telemetry_type=TelemeryType.TIMEOUT_CLOSE_CAS_FAILURE,
                telemetry_message="CONCURRENT_THREAD_EXECUTION",
                error=ex,
            )
        except ThreadNotFoundError as ex:
            return self._generate_runtime_error(
                phase_context=phase_context,
                user_message="UNKNOWN_THREAD",
                telemetry_type=TelemeryType.RUNTIME_UNKNOWN_THREAD_FAILURE,
                telemetry_message="UNKNOWN_THREAD",
                error=ex,
            )

    def _generate_runtime_error(
        self,
        phase_context: PhaseContext,
        user_message: str,
        telemetry_type: TelemeryType,
        telemetry_message: str,
        error: Optional[Exception] = None,
    ) -> RuntimeEvent:
        """
        Helper method that first emits a TelemetryEvent for error and then creates a RuntimeEvent
        """
        # first emit telemetry event
        try:
            self._telemetry_policy.emit(
                TelemetryEvent.error(
                    type=telemetry_type,
                    component=TelemetryComponent.RUNTIME,
                    message=telemetry_message,
                    exception=error,
                )
            )
        except Exception:
            pass

        return RuntimeEvent(
            type=RuntimeEventType.ERROR,
            phase_id=phase_context.phase_id,
            thread_id=phase_context.thread_id,
            correlation_id=phase_context.correlation_id,
            trace_id=phase_context.trace_id,
            content=[TextPart(text=user_message)],
        )

    async def _execute_orchestration(
        self,
        thread_context: ThreadContext,
        phase_context: PhaseContext,
    ) -> AsyncIterator[RuntimeEvent]:

        try:
            async for agent_event in self._orchestration.execute(
                thread_context=thread_context,
                phase_context=phase_context,
            ):
                # emit non-terminal events
                if not agent_event.is_terminal:
                    # yield and continue non-terminal events
                    yield RuntimeEventFactory.create_runtime_event(
                        agent_event=agent_event,
                        phase_context=phase_context,
                    )
                    continue

                # convert terminal event to thread entry
                entry = ThreadEntryFactory.create_entry(agent_event=agent_event, phase_context=phase_context)

                store_event = await self._append_entry(
                    entry, thread_context.last_entry.entry_id, phase_context=phase_context
                )
                if store_event:
                    yield store_event
                    return

                # reload the thread context
                entries = await self._store.load(thread_id=phase_context.thread_id)
                thread_context = ThreadContext(entries=entries)

                # check if last entry is SuspendEntry, if so generate ResumeToken
                resume_token = None
                if isinstance(thread_context.last_entry, SuspendEntry):
                    resume_token = self._resume_service.create_token(thread_context.last_entry)

                # yield runtime event from agent event
                yield RuntimeEventFactory.create_runtime_event(
                    agent_event=agent_event, phase_context=phase_context, resume_token=resume_token
                )
                return

        except Exception as ex:
            # first create ErrorEntry for the thread log
            await self._append_entry(
                ErrorEntry(
                    thread_id=phase_context.thread_id,
                    phase_id=phase_context.phase_id,
                    previous_entry_id=thread_context.last_entry.entry_id,
                    content=[TextPart(text="ORCHESTRATION_EXECUTION_FAILURE")],
                    agent_id="SYSTEM",
                ),
                expected_previous_entry_id=thread_context.last_entry.entry_id,
                phase_context=phase_context,
            )

            # now emit an error runtime event
            yield self._generate_runtime_error(
                phase_context=phase_context,
                user_message="ORCHESTRATION_EXECUTION_FAILURE",
                telemetry_type=TelemeryType.RUNTIME_PHASE_ERROR,
                telemetry_message="ORCHESTRATION_EXECUTION_FAILURE",
                error=ex,
            )

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)
