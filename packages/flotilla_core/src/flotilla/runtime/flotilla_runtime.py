# flotilla/runtime/flotilla_runtime.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional, Union

from flotilla.runtime.runtime_request import (
    RuntimeRequest,
)
from flotilla.runtime.runtime_response import (
    RuntimeResponse,
    RuntimeReseponseType,
)
from flotilla.runtime.runtime_event import RuntimeEvent, RuntimeEventType, RuntimeEventFactory

from flotilla.runtime.phase_context import PhaseContext
from flotilla.runtime.phase_context_service import DefaultPhaseContextService, PhaseContextService
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
    ActorType,
)

from flotilla.timeout.execution_timeout_policy import ExecutionTimeoutPolicy
from flotilla.suspend.suspend_service import SuspendService
from flotilla.suspend.resume_service import DefaultResumeService, ResumeService
from flotilla.suspend.errors import ResumeAuthorizationError, ResumeTokenExpiredError, ResumeTokenInvalidError
from flotilla.runtime.orchestration_strategy import OrchestrationStrategy
from flotilla.telemetry.telemetry_service import TelemetryService
from flotilla.telemetry.telemetry_event import TelemetryEvent
from flotilla.telemetry.telemetry_types import TelemetryType, TelemetryComponent
from flotilla.timeout.default_execution_timeout_policy import DefaultExecutionTimeoutPolicy
from flotilla.suspend.permissive_resume_authorization_policy import PermissiveResumeAuthorizationPolicy
from flotilla.suspend.no_op_suspend_service import NoOpSuspendService
from flotilla.telemetry.logging_telemetry_service import LoggingTelemetryService
from flotilla.utils.logger import get_logger

# AgentEvent

logger = get_logger(__name__)


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
        phase_context_service: Optional[PhaseContextService] = None,
        execution_timeout_policy: Optional[ExecutionTimeoutPolicy] = None,
        resume_service: Optional[ResumeService] = None,
        suspend_service: Optional[SuspendService] = None,
        telemetry_service: Optional[TelemetryService] = None,
    ):
        self._orchestration = orchestration
        self._store = store
        self._phase_context_service = phase_context_service or DefaultPhaseContextService()
        self._timeout_policy = execution_timeout_policy or DefaultExecutionTimeoutPolicy(timeout_ms=300000)
        self._resume_service = resume_service or DefaultResumeService(
            resume_authorization_policy=PermissiveResumeAuthorizationPolicy(), ttl_seconds=432000
        )
        self._suspend_service = suspend_service or NoOpSuspendService()
        self._telemetry_service = telemetry_service or LoggingTelemetryService()

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
        self._emit_info(
            TelemetryType.RUNTIME_PHASE_STARTED,
            "Runtime phase started",
            phase_context,
            has_resume_token=bool(request.resume_token),
            content_part_count=len(request.content),
        )
        logger.debug(
            "Runtime phase context created for thread '%s' phase '%s' using %s",
            phase_context.thread_id,
            phase_context.phase_id,
            type(self._phase_context_service).__name__,
        )

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
                logger.debug(
                    "Build resume entry for thread '%s' phase '%s' from supplied token",
                    phase_context.thread_id,
                    phase_context.phase_id,
                )
                entry = await self._resume_service.build_resume_entry(
                    request=request, phase_context=phase_context, thread_context=thread_context
                )
            except ResumeAuthorizationError as ex:
                yield self._generate_runtime_error(
                    phase_context=phase_context,
                    user_message="USER_NOT_AUTHORIZED",
                    telemetry_type=TelemetryType.RUNTIME_RESUME_REJECTED,
                    telemetry_message="Runtime resume rejected",
                    error=ex,
                    telemetry_severity="WARNING",
                    telemetry_attributes={"reason": "unauthorized"},
                )
                return
            except (ResumeTokenInvalidError, ResumeTokenExpiredError) as ex:
                reason = "expired_token" if isinstance(ex, ResumeTokenExpiredError) else "invalid_token"
                yield self._generate_runtime_error(
                    phase_context=phase_context,
                    user_message="INVALID_RESUME_TOKEN",
                    telemetry_type=TelemetryType.RUNTIME_RESUME_REJECTED,
                    telemetry_message="Runtime resume rejected",
                    error=ex,
                    telemetry_severity="WARNING",
                    telemetry_attributes={"reason": reason},
                )
                return
        else:
            #   6.  Construct UserInput:
            entry = UserInput(
                thread_id=request.thread_id,
                phase_id=phase_context.phase_id,
                previous_entry_id=previous_entry_id,
                content=request.content,
                actor_id=request.user_id,
            )

        #   7.  Attempt CAS append of start entry.
        event = await self._append_entry(
            entry=entry,
            expected_previous_entry_id=previous_entry_id,
            phase_context=phase_context,
        )
        if event:
            yield event
            return
        logger.debug(
            "Appended runtime start entry of type %s for thread '%s' phase '%s'",
            type(entry).__name__,
            phase_context.thread_id,
            phase_context.phase_id,
        )

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
            logger.debug(
                "Loaded thread '%s' with %d entries for phase '%s'",
                thread_id,
                len(entries),
                phase_context.phase_id,
            )
            return ThreadContext(entries=entries)

        except ThreadNotFoundError as ex:
            return self._generate_runtime_error(
                phase_context=phase_context,
                user_message="UNKNOWN_THREAD",
                telemetry_type=TelemetryType.RUNTIME_THREAD_NOT_FOUND,
                telemetry_message="Thread not found",
                error=ex,
                telemetry_severity="WARNING",
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

        logger.debug(
            "Checked timeout for active thread '%s' phase '%s': expired=%s policy=%s active_entry_id=%s",
            phase_context.thread_id,
            phase_context.phase_id,
            expired,
            type(self._timeout_policy).__name__,
            thread_context.last_entry.entry_id,
        )

        # thread still running and not expired
        if not expired:
            return self._generate_runtime_error(
                phase_context=phase_context,
                user_message="CONCURRENT_THREAD_EXECUTION",
                telemetry_type=TelemetryType.RUNTIME_ACTIVE_THREAD_REJECTED,
                telemetry_message="Thread still running",
                telemetry_severity="WARNING",
            )

        # thread expired -> attempt timeout close
        event = await self._append_entry(
            ErrorEntry(
                thread_id=request.thread_id,
                phase_id=thread_context.last_entry.phase_id,
                previous_entry_id=thread_context.last_entry.entry_id,
                content=[TextPart(text="EXECUTION_TIMEOUT")],
                actor_id="RUNTIME",
                actor_type=ActorType.SYSTEM,
            ),
            expected_previous_entry_id=thread_context.last_entry.entry_id,
            phase_context=phase_context,
        )
        if event is None:
            self._emit_info(
                TelemetryType.RUNTIME_TIMEOUT_CLOSED,
                "Closed expired active thread phase",
                phase_context,
                expired_phase_id=thread_context.last_entry.phase_id,
                expired_entry_id=thread_context.last_entry.entry_id,
            )
        return event

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
            logger.warning(
                "Thread entry append rejected by optimistic concurrency check for thread '%s' phase '%s'",
                phase_context.thread_id,
                phase_context.phase_id,
                exc_info=True,
            )
            return self._generate_runtime_error(
                phase_context=phase_context,
                user_message="CONCURRENT_THREAD_EXECUTION",
                telemetry_type=TelemetryType.RUNTIME_PHASE_FAILED,
                telemetry_message="CONCURRENT_THREAD_EXECUTION",
                error=ex,
                telemetry_severity="WARNING",
                telemetry_attributes={"reason": "append_conflict"},
            )
        except ThreadNotFoundError as ex:
            return self._generate_runtime_error(
                phase_context=phase_context,
                user_message="UNKNOWN_THREAD",
                telemetry_type=TelemetryType.RUNTIME_THREAD_NOT_FOUND,
                telemetry_message="UNKNOWN_THREAD",
                error=ex,
                telemetry_severity="WARNING",
            )

    def _generate_runtime_error(
        self,
        phase_context: PhaseContext,
        user_message: str,
        telemetry_type: TelemetryType,
        telemetry_message: str,
        error: Optional[Exception] = None,
        telemetry_severity: str = "ERROR",
        telemetry_attributes: Optional[dict[str, Any]] = None,
    ) -> RuntimeEvent:
        """
        Helper method that first emits a TelemetryEvent for error and then creates a RuntimeEvent
        """
        self._emit_telemetry(
            telemetry_severity,
            telemetry_type,
            telemetry_message,
            phase_context,
            error=error,
            **(telemetry_attributes or {}),
        )

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
                logger.debug(
                    "Received agent event %s for thread '%s' phase '%s' terminal=%s",
                    agent_event.type,
                    phase_context.thread_id,
                    phase_context.phase_id,
                    agent_event.is_terminal,
                )
                if not agent_event.is_terminal:
                    # yield and continue non-terminal events
                    yield RuntimeEventFactory.create_runtime_event(
                        agent_event=agent_event,
                        phase_context=phase_context,
                    )
                    continue

                # convert terminal event to thread entry
                entry = ThreadEntryFactory.create_entry_from_agent_event(
                    agent_event=agent_event, phase_context=phase_context
                )

                store_event = await self._append_entry(
                    entry,
                    thread_context.last_entry.entry_id,
                    phase_context=phase_context,
                )
                if store_event:
                    yield store_event
                    return
                logger.debug(
                    "Appended runtime terminal entry of type %s for thread '%s' phase '%s'",
                    type(entry).__name__,
                    phase_context.thread_id,
                    phase_context.phase_id,
                )

                # reload the thread context
                entries = await self._store.load(thread_id=phase_context.thread_id)
                logger.debug(
                    "Reloaded thread '%s' with %d entries after terminal append",
                    phase_context.thread_id,
                    len(entries),
                )
                thread_context = ThreadContext(entries=entries)

                # check if last entry is SuspendEntry, if so generate ResumeToken
                resume_token = None
                if isinstance(thread_context.last_entry, SuspendEntry):
                    resume_token = self._resume_service.create_token(thread_context.last_entry)
                    try:
                        await self._suspend_service.handle_suspend(
                            thread_context=thread_context,
                            suspend_entry=thread_context.last_entry,
                            resume_token=resume_token,
                            phase_context=phase_context,
                        )
                    except Exception:
                        logger.warning(
                            "Suspend handler failed after suspend entry '%s' was stored for thread '%s'",
                            thread_context.last_entry.entry_id,
                            phase_context.thread_id,
                            exc_info=True,
                        )

                # yield runtime event from agent event
                event_type = (
                    TelemetryType.RUNTIME_PHASE_SUSPENDED
                    if isinstance(thread_context.last_entry, SuspendEntry)
                    else TelemetryType.RUNTIME_PHASE_COMPLETED
                )
                self._emit_info(
                    event_type,
                    "Runtime phase reached terminal event",
                    phase_context,
                    runtime_event_type=agent_event.type,
                    terminal_entry_type=type(thread_context.last_entry).__name__,
                    terminal_entry_id=thread_context.last_entry.entry_id,
                )
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
                    actor_id="SYSTEM",
                ),
                expected_previous_entry_id=thread_context.last_entry.entry_id,
                phase_context=phase_context,
            )

            # now emit an error runtime event
            yield self._generate_runtime_error(
                phase_context=phase_context,
                user_message="ORCHESTRATION_EXECUTION_FAILURE",
                telemetry_type=TelemetryType.RUNTIME_PHASE_FAILED,
                telemetry_message="ORCHESTRATION_EXECUTION_FAILURE",
                error=ex,
            )

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _emit_info(
        self,
        telemetry_type: TelemetryType,
        message: str,
        phase_context: PhaseContext,
        **attributes: Any,
    ) -> None:
        self._emit_telemetry("INFO", telemetry_type, message, phase_context, **attributes)

    def _emit_warning(
        self,
        telemetry_type: TelemetryType,
        message: str,
        phase_context: PhaseContext,
        error: Optional[Exception] = None,
        **attributes: Any,
    ) -> None:
        self._emit_telemetry("WARNING", telemetry_type, message, phase_context, error=error, **attributes)

    def _emit_telemetry(
        self,
        severity: str,
        telemetry_type: TelemetryType,
        message: str,
        phase_context: PhaseContext,
        error: Optional[Exception] = None,
        **attributes: Any,
    ) -> None:
        try:
            event_attributes = {"message": message, **attributes}
            if error is not None:
                event_attributes["exception"] = str(error)

            self._telemetry_service.emit(
                TelemetryEvent(
                    event_type=telemetry_type,
                    component=TelemetryComponent.RUNTIME,
                    severity=severity,
                    context={
                        "thread_id": phase_context.thread_id,
                        "phase_id": phase_context.phase_id,
                        "correlation_id": phase_context.correlation_id,
                        "trace_id": phase_context.trace_id,
                    },
                    attributes=event_attributes,
                )
            )
        except Exception:
            pass
