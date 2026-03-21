import pytest

from flotilla.thread.thread_context import ThreadContext, ThreadStatus
from flotilla.thread.thread_entries import (
    UserInput,
    AgentOutput,
    SuspendEntry,
    ResumeEntry,
    ErrorEntry,
    ClosedEntry,
)

from flotilla.runtime.content_part import TextPart


def make_text(text: str):
    return TextPart(type="text", text=text)


# ----------------------------------------------------------
# EMPTY THREAD
# ----------------------------------------------------------


def test_empty_thread_valid_and_ready():
    ctx = ThreadContext(entries=[])
    assert ctx.status == ThreadStatus.READY


# ----------------------------------------------------------
# THREAD ID VALIDATION
# ----------------------------------------------------------


def test_thread_id_mismatch_rejected():
    e1 = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[make_text("hi")],
    )

    e2 = AgentOutput(
        thread_id="t2",
        phase_id="p1",
        entry_id="e2",
        previous_entry_id="e1",
        actor_id="a1",
        content=[make_text("hello")],
    )

    with pytest.raises(ValueError):
        ThreadContext(entries=[e1, e2])


# ----------------------------------------------------------
# LINKED LIST VALIDATION
# ----------------------------------------------------------


def test_previous_entry_link_must_match():
    e1 = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[make_text("hi")],
    )

    e2 = AgentOutput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e2",
        previous_entry_id="wrong",
        actor_id="a1",
        content=[make_text("bad")],
    )

    with pytest.raises(ValueError):
        ThreadContext(entries=[e1, e2])


def test_first_entry_previous_must_be_none():
    e1 = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        previous_entry_id="illegal",
        actor_id="u1",
        content=[make_text("hi")],
    )

    with pytest.raises(ValueError):
        ThreadContext(entries=[e1])


# ----------------------------------------------------------
# START ENTRY TRANSITIONS
# ----------------------------------------------------------


def test_start_entry_must_be_followed_by_terminal():
    e1 = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[make_text("hi")],
    )

    e2 = UserInput(
        thread_id="t1",
        phase_id="p2",
        entry_id="e2",
        previous_entry_id="e1",
        actor_id="u1",
        content=[make_text("invalid")],
    )

    with pytest.raises(ValueError):
        ThreadContext(entries=[e1, e2])


def test_userinput_followed_by_agentoutput_valid():
    e1 = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[make_text("hi")],
    )

    e2 = AgentOutput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e2",
        previous_entry_id="e1",
        actor_id="a1",
        content=[make_text("done")],
    )

    ctx = ThreadContext(entries=[e1, e2])

    assert ctx.status == ThreadStatus.READY


def test_userinput_followed_by_error_valid():
    e1 = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[make_text("hi")],
    )

    e2 = ErrorEntry(
        thread_id="t1",
        phase_id="p1",
        entry_id="e2",
        previous_entry_id="e1",
        actor_id="a1",
        content=[make_text("done")],
    )

    ctx = ThreadContext(entries=[e1, e2])

    assert ctx.status == ThreadStatus.READY


def test_userinput_followed_by_suspend_valid():
    e1 = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[make_text("start")],
    )

    e2 = SuspendEntry(
        thread_id="t1",
        phase_id="p1",
        entry_id="e2",
        previous_entry_id="e1",
        actor_id="a1",
        content=[make_text("approval needed")],
    )

    ctx = ThreadContext(entries=[e1, e2])

    assert ctx.status == ThreadStatus.SUSPENDED


# ----------------------------------------------------------
# TERMINAL ENTRY TRANSITIONS
# ----------------------------------------------------------


def test_terminal_entry_must_be_followed_by_start():
    e1 = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[make_text("start")],
    )

    e2 = AgentOutput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e2",
        previous_entry_id="e1",
        actor_id="a1",
        content=[make_text("done")],
    )

    e3 = AgentOutput(
        thread_id="t1",
        phase_id="p2",
        entry_id="e3",
        previous_entry_id="e2",
        actor_id="a1",
        content=[make_text("invalid")],
    )

    with pytest.raises(ValueError):
        ThreadContext(entries=[e1, e2, e3])


def test_terminal_followed_by_userinput_valid():
    e1 = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[make_text("start")],
    )

    e2 = AgentOutput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e2",
        previous_entry_id="e1",
        actor_id="a1",
        content=[make_text("done")],
    )

    e3 = UserInput(
        thread_id="t1",
        phase_id="p2",
        entry_id="e3",
        previous_entry_id="e2",
        actor_id="u1",
        content=[make_text("next")],
    )

    ctx = ThreadContext(entries=[e1, e2, e3])

    assert ctx.status == ThreadStatus.RUNNING


# ----------------------------------------------------------
# SUSPEND / RESUME TRANSITIONS
# ----------------------------------------------------------


def test_suspend_requires_resume():
    e1 = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[make_text("start")],
    )

    e2 = SuspendEntry(
        thread_id="t1",
        phase_id="p1",
        entry_id="e2",
        previous_entry_id="e1",
        actor_id="a1",
        content=[make_text("approval")],
    )

    e3 = UserInput(
        thread_id="t1",
        phase_id="p2",
        entry_id="e3",
        previous_entry_id="e2",
        actor_id="u1",
        content=[make_text("invalid")],
    )

    with pytest.raises(ValueError):
        ThreadContext(entries=[e1, e2, e3])


def test_suspend_followed_by_resume_valid():
    e1 = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[make_text("start")],
    )

    e2 = SuspendEntry(
        thread_id="t1",
        phase_id="p1",
        entry_id="e2",
        previous_entry_id="e1",
        actor_id="a1",
        content=[make_text("approval needed")],
    )

    e3 = ResumeEntry(
        thread_id="t1",
        phase_id="p2",
        entry_id="e3",
        previous_entry_id="e2",
        actor_id="u1",
        content=[make_text("approved")],
    )

    ctx = ThreadContext(entries=[e1, e2, e3])

    assert ctx.status == ThreadStatus.RUNNING


# ----------------------------------------------------------
# CLOSED THREAD
# ----------------------------------------------------------


def test_closed_entry_sets_closed_status():
    e1 = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[make_text("start")],
    )

    e2 = ClosedEntry(
        thread_id="t1",
        phase_id="p1",
        entry_id="e2",
        previous_entry_id="e1",
        actor_id="u1",
        content=[make_text("deleted")],
    )

    ctx = ThreadContext(entries=[e1, e2])

    assert ctx.status == ThreadStatus.CLOSED


def test_closed_entry_prevents_future_entries():
    e1 = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[make_text("start")],
    )

    e2 = ClosedEntry(
        thread_id="t1",
        phase_id="p1",
        entry_id="e2",
        previous_entry_id="e1",
        actor_id="u1",
        content=[make_text("close")],
    )

    e3 = UserInput(
        thread_id="t1",
        phase_id="p2",
        entry_id="e3",
        previous_entry_id="e2",
        actor_id="u1",
        content=[make_text("illegal")],
    )

    with pytest.raises(ValueError):
        ThreadContext(entries=[e1, e2, e3])
