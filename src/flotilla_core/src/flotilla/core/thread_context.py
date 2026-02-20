from typing import List
from pydantic import BaseModel, model_validator
from enum import Enum

from flotilla.core.thread_entries import (
    ThreadEntry,
    SuspendEntry,
    ResumeEntry,
    ClosedEntry,
)


class ThreadStatus(str, Enum):
    RUNNABLE = "runnable"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class ThreadContext(BaseModel):
    entries: List[ThreadEntry]

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True,
    }

    # ---------------------------
    # Validation
    # ---------------------------

    @model_validator(mode="after")
    def validate_thread(self):
        if not self.entries:
            raise ValueError("ThreadContext cannot be empty")

        self._validate_thread_id_consistency()
        self._validate_structure()

        return self

    # ---------------------------
    # Derived Properties
    # ---------------------------

    @property
    def thread_id(self) -> str:
        return self.entries[0].thread_id

    @property
    def last_entry(self) -> "ThreadEntry":
        return self.entries[-1]

    @property
    def status(self) -> ThreadStatus:
        last = self.entries[-1]

        if isinstance(last, SuspendEntry):
            return ThreadStatus.SUSPENDED

        if isinstance(last, ClosedEntry):
            return ThreadStatus.CLOSED

        return ThreadStatus.RUNNABLE

    # ---------------------------
    # Structural Validation
    # ---------------------------

    def _validate_thread_id_consistency(self):
        thread_id = self.entries[0].thread_id
        for entry in self.entries:
            if entry.thread_id != thread_id:
                raise ValueError(
                    "All ThreadEntry objects must share the same thread_id"
                )

    def _validate_structure(self):
        suspended = False

        for i, entry in enumerate(self.entries):
            is_last = i == len(self.entries) - 1

            # 1️⃣ No entries after ClosedEntry
            if isinstance(entry, ClosedEntry) and not is_last:
                raise ValueError("No entries allowed after ClosedEntry")

            # 2️⃣ Suspend handling
            if isinstance(entry, SuspendEntry):
                if suspended:
                    raise ValueError("Consecutive SuspendEntry not allowed")

                suspended = True

                if not is_last:
                    next_entry = self.entries[i + 1]
                    if not isinstance(next_entry, ResumeEntry):
                        raise ValueError("SuspendEntry must be followed by ResumeEntry")

            # 3️⃣ Resume handling
            if isinstance(entry, ResumeEntry):
                if not suspended:
                    raise ValueError("ResumeEntry must follow SuspendEntry")
                suspended = False
