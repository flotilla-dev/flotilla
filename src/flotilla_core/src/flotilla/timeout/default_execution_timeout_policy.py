from .execution_timeout_policy import ExecutionTimeoutPolicy
from flotilla.thread.thread_context import ThreadContext
from datetime import datetime


class DefaultExecutionTimeoutPolicy(ExecutionTimeoutPolicy):

    def __init__(self, timeout_ms: int):
        self._timeout_ms = timeout_ms

    def is_expired(self, thread_context: ThreadContext, now: datetime):
        if not thread_context.has_active_phase():
            return False

        start_ts = thread_context.active_phase_start_timestamp()
        elapsed_ms = (now - start_ts).total_seconds() * 1000

        return elapsed_ms > self._timeout_ms
