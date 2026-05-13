from abc import ABC, abstractmethod

from flotilla.runtime.phase_context import PhaseContext
from flotilla.thread.thread_entries import SuspendEntry
from flotilla.suspend.resume_token_payload import ResumeTokenPayload


class ResumeAuthorizationPolicy(ABC):
    """
    Policy that decides whether a valid resume token may be used.

    DefaultResumeService calls this after it has decoded the token, verified
    expiration, matched it to the requested thread, and confirmed the durable
    thread tail is the expected SuspendEntry. The policy answers the remaining
    permission question: is this resume attempt allowed for the suspended work?

    Implementations should make a decision only. They should not append thread
    entries, create tokens, or notify external systems.
    """

    @abstractmethod
    async def is_authorized(
        self,
        *,
        payload: ResumeTokenPayload,
        suspend_entry: SuspendEntry,
        phase_context: PhaseContext,
    ) -> bool: ...
