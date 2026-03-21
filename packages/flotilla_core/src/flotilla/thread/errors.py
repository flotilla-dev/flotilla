from __future__ import annotations
from typing import Optional
from flotilla.flotilla_error import FlotillaError


class AppendConflictError(FlotillaError):
    def __init__(
        self,
        thread_id: str,
        phase_id: str,
        tail_entry_id: Optional[str] = None,
        expected_entry_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            thread_id=thread_id,
            phase_id=phase_id,
            tail_entry_id=tail_entry_id,
            expected_entry_id=expected_entry_id,
        )


class ConcurrentThreadExecutionError(FlotillaError):
    """Exception raised when the ThreadEntryStore CAS check fails."""

    def __init__(
        self,
        thread_id: str,
        phase_id: str,
        tail_entry_id: str,
        expected_entry_id: str,
        entry_type: str,
        message: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            thread_id=thread_id,
            phase_id=phase_id,
            tail_entry_id=tail_entry_id,
            expected_entry_id=expected_entry_id,
            entry_type=entry_type,
        )


class ThreadNotFoundError(FlotillaError):
    """Exception raised when the designated thread cannot be found."""

    def __init__(self, thread_id: str, message: Optional[str] = None):
        super().__init__(message=message, thread_id=thread_id)
