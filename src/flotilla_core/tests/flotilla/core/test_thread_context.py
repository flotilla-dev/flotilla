import pytest
from flotilla.core.thread_context import ThreadContext, ThreadStatus
from flotilla.core.thread_entries import (
    UserInput,
    AgentOutput,
    SuspendEntry,
    ResumeEntry,
    ClosedEntry,
)
from flotilla.core.content_part import TextPart


def make_text(text: str):
    return TextPart(type="text", text=text)


def test_empty_thread_rejected():
    with pytest.raises(ValueError):
        ThreadContext(entries=[])


def test_thread_id_mismatch_rejected():
    e1 = UserInput(thread_id="t1", content=[make_text("hi")])
    e2 = AgentOutput(thread_id="t2", content=[make_text("hello")])

    with pytest.raises(ValueError):
        ThreadContext(entries=[e1, e2])


def test_closed_entry_must_be_last():
    e1 = UserInput(thread_id="t1", content=[make_text("hi")])
    e2 = ClosedEntry(thread_id="t1")
    e3 = AgentOutput(thread_id="t1", content=[make_text("bad")])

    with pytest.raises(ValueError):
        ThreadContext(entries=[e1, e2, e3])


def test_suspend_as_last_entry_is_valid_and_sets_status():
    e1 = UserInput(thread_id="t1", entry_id="e1", content=[make_text("hi")])
    e2 = SuspendEntry(
        thread_id="t1", entry_id="e2", content=[TextPart(text="approval")]
    )

    ctx = ThreadContext(entries=[e1, e2])

    assert ctx.status == ThreadStatus.SUSPENDED


def test_suspend_not_last_requires_resume():
    e1 = UserInput(thread_id="t1", content=[make_text("hi")])
    e2 = SuspendEntry(thread_id="t1", content=[TextPart(text="approval")])
    e3 = UserInput(thread_id="t1", content=[make_text("illegal")])

    with pytest.raises(ValueError):
        ThreadContext(entries=[e1, e2, e3])


def test_resume_without_suspend_rejected():
    e1 = UserInput(thread_id="t1", entry_id="e1", content=[make_text("hi")])
    e2 = ResumeEntry(thread_id="t1", entry_id="e2", content=[TextPart(text="approved")])

    with pytest.raises(ValueError):
        ThreadContext(entries=[e1, e2])


def test_status_runnable():
    e1 = UserInput(thread_id="t1", content=[make_text("hi")])
    ctx = ThreadContext(entries=[e1])
    assert ctx.status == ThreadStatus.RUNNABLE


def test_status_suspended():
    e1 = UserInput(thread_id="t1", entry_id="e1", content=[make_text("hi")])
    e2 = SuspendEntry(
        thread_id="t1", entry_id="e2", content=[TextPart(text="apporoval needed")]
    )
    e3 = ResumeEntry(thread_id="t1", entry_id="e3", content=[TextPart(text="approved")])
    e4 = SuspendEntry(
        thread_id="t1", entry_id="e4", content=[TextPart(text="approval needed")]
    )

    ctx = ThreadContext(entries=[e1, e2, e3, e4])
    assert ctx.status == ThreadStatus.SUSPENDED


def test_status_closed():
    e1 = UserInput(thread_id="t1", content=[make_text("hi")])
    e2 = ClosedEntry(thread_id="t1")
    ctx = ThreadContext(entries=[e1, e2])
    assert ctx.status == ThreadStatus.CLOSED
