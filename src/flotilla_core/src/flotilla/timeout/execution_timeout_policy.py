from typing import Protocol
from flotilla.thread.thread_context import ThreadContext
from datetime import datetime


class ExecutionTimeoutPolicy(Protocol):

    def is_expired(self, thread_context: ThreadContext, now: datetime) -> bool: ...
