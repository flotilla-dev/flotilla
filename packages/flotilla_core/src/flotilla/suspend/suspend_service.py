from abc import ABC, abstractmethod

from flotilla.thread.thread_context import ThreadContext
from flotilla.thread.thread_entries import SuspendEntry
from flotilla.runtime.phase_context import PhaseContext


class SuspendService(ABC):
    """
    Post-suspend action hook for external notification and routing.

    FlotillaRuntime calls this service only after an agent has emitted a
    terminal suspend event, the corresponding SuspendEntry has been durably
    appended, the thread has been reloaded, and a resume token has been
    created. Implementations can notify users, enqueue approval work, publish
    events, or integrate with external systems.

    This service must not mutate thread state or decide whether suspension is
    allowed. Failures are treated as best-effort and non-fatal by the runtime.
    """

    @abstractmethod
    async def handle_suspend(
        self,
        thread_context: ThreadContext,
        suspend_entry: SuspendEntry,
        resume_token: str,
        phase_context: PhaseContext,
    ) -> None: ...
