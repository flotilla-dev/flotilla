from typing import Protocol
from flotilla.runtime.runtime_request import RuntimeRequest
from flotilla.thread.thread_entries import SuspendEntry


class ResumeAuthorizationPolicy(Protocol):

    def is_authorized(
        self,
        *,
        request: RuntimeRequest,
        suspend_entry: SuspendEntry,
    ) -> bool: ...
