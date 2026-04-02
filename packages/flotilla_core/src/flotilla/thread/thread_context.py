from typing import List
from pydantic import BaseModel, model_validator
from enum import Enum

from flotilla.thread.thread_entries import (
    ThreadEntry,
    SuspendEntry,
    ResumeEntry,
    ClosedEntry,
    UserInput,
    AgentOutput,
    ErrorEntry,
)


class ThreadStatus(str, Enum):
    READY = "ready"
    RUNNING = "running"
    SUSPENDED = "suspended"
    CLOSED = "closed"


StartEntryTypes = (UserInput, ResumeEntry)
TerminalEntryTypes = (AgentOutput, SuspendEntry, ErrorEntry, ClosedEntry)


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
        if self.entries is None:
            raise ValueError("ThreadContext.entries cannot be None")

        self._validate_thread_id_consistency()
        self._validate_structure()

        return self

    # ---------------------------
    # Derived Properties
    # ---------------------------

    @property
    def thread_id(self) -> str:
        if not self.entries:
            return None
        else:
            return self.entries[0].thread_id

    @property
    def last_entry(self) -> ThreadEntry:
        if not self.entries:
            return None
        else:
            return self.entries[-1]

    @property
    def status(self) -> ThreadStatus:
        if not self.entries:
            return ThreadStatus.READY

        last = self.entries[-1]

        if isinstance(last, SuspendEntry):
            return ThreadStatus.SUSPENDED

        if isinstance(last, ClosedEntry):
            return ThreadStatus.CLOSED

        if isinstance(last, (AgentOutput, ErrorEntry)):
            return ThreadStatus.READY

        return ThreadStatus.RUNNING

    # ---------------------------
    # Structural Validation
    # ---------------------------
    def _validate_thread_id_consistency(self):
        # return if list is empty
        if not self.entries:
            return

        thread_id = self.entries[0].thread_id
        for entry in self.entries:
            if entry.thread_id != thread_id:
                raise ValueError("All ThreadEntry objects must share the same thread_id")

    def _validate_structure(self) -> None:
        entries = self.entries

        if not entries:
            return

        # first entry must not reference previous
        first = entries[0]
        if first.previous_entry_id is not None:
            raise ValueError("First entry must have previous_entry_id=None")

        for prev, curr in zip(entries, entries[1:]):

            # linked list integrity
            if curr.previous_entry_id != prev.entry_id:
                raise ValueError("Invalid previous_entry_id linkage")

            # CLOSED state
            if isinstance(prev, ClosedEntry):
                raise ValueError("No entries allowed after ClosedEntry")

            # RUNNING state
            if isinstance(prev, (UserInput, ResumeEntry)):
                if not isinstance(curr, (AgentOutput, ErrorEntry, SuspendEntry, ClosedEntry)):
                    raise ValueError("Start entry must be followed by a terminal entry")

            # READY state
            elif isinstance(prev, (AgentOutput, ErrorEntry)):
                if not isinstance(curr, (UserInput, ClosedEntry)):
                    raise ValueError("Terminal entry must be followed by UserInput")

            # SUSPENDED state
            elif isinstance(prev, SuspendEntry):
                if not isinstance(curr, ResumeEntry):
                    raise ValueError("SuspendEntry must be followed by ResumeEntry")
