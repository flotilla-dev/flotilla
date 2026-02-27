import pytest
from flotilla.core.thread_entries import (
    ThreadEntry,
    UserInput,
    AgentOutput,
    SuspendEntry,
)
from flotilla.runtime.content_part import TextPart
from pydantic import ValidationError


def make_text(text: str):
    return TextPart(type="text", text=text)


def test_thread_entry_is_immutable():
    entry = ThreadEntry(thread_id="t1")
    with pytest.raises(ValidationError):
        entry.thread_id = "t2"


def test_user_input_requires_content():
    with pytest.raises(ValidationError):
        UserInput(thread_id="t1", content=[])


def test_agent_output_is_serializable():
    entry = AgentOutput(thread_id="t1", content=[make_text("hello")])
    dumped = entry.model_dump()
    assert dumped["thread_id"] == "t1"


def test_suspend_requires_reason():
    with pytest.raises(Exception):
        SuspendEntry(thread_id="t1", reason=None)
