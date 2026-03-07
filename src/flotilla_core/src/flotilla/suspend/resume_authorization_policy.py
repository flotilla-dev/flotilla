from typing import Protocol
from flotilla.thread.thread_entries import SuspendEntry
from flotilla.suspend.resume_token_payload import ResumeTokenPayload


class ResumeAuthorizationPolicy(Protocol):

    async def is_authorized(
        self,
        *,
        payload: ResumeTokenPayload,
        suspend_entry: SuspendEntry,
    ) -> bool: ...
