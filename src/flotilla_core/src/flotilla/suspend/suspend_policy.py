from typing import Protocol
from flotilla.thread.thread_context import ThreadContext
from flotilla.thread.thread_entries import SuspendEntry
from flotilla.runtime.execution_config import ExecutionConfig


class SuspendPolicy(Protocol):

    async def handle_suspend(
        thread_context: ThreadContext,
        suspend_entry: SuspendEntry,
        resume_token: str,
        execution_config: ExecutionConfig,
    ) -> None: ...
