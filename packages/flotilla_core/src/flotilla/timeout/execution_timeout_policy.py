from abc import ABC, abstractmethod
from datetime import datetime

from flotilla.thread.thread_context import ThreadContext


class ExecutionTimeoutPolicy(ABC):
    """
    Policy that decides whether an active runtime phase has timed out.

    When a new request arrives for a thread whose last durable entry is still
    running, FlotillaRuntime asks this policy whether that active phase should
    be considered expired. A true result allows runtime to append a timeout
    ErrorEntry; a false result causes the new request to be rejected as
    concurrent execution.

    Implementations should make a deterministic decision from ThreadContext
    and the supplied clock value. They should not mutate thread state.
    """

    @abstractmethod
    def is_expired(self, thread_context: ThreadContext, now: datetime) -> bool: ...
