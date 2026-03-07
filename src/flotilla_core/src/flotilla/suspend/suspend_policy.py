from typing import Protocol
from flotilla.thread.thread_context import ThreadContext
from flotilla.thread.thread_entries import SuspendEntry
from flotilla.runtime.phase_context import PhaseContext


class SuspendPolicy(Protocol):

    async def handle_suspend(
        thread_context: ThreadContext,
        suspend_entry: SuspendEntry,
        resume_token: str,
        execution_config: PhaseContext,
    ) -> None: ...
