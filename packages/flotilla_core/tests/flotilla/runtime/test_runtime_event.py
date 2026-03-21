import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from flotilla.runtime.runtime_event import (
    RuntimeEvent,
    RuntimeEventFactory,
    RuntimeEventType,
)

from flotilla.agents.agent_event import AgentEvent
from flotilla.runtime.phase_context import PhaseContext
from flotilla.runtime.content_part import TextPart


# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------


def make_phase_context():
    return PhaseContext(
        thread_id="t1",
        phase_id="p1",
        correlation_id="corr-1",
        trace_id="trace-1",
        user_id="u1",
        agent_config={},
    )


def make_text(text: str):
    return TextPart(text=text)


# -----------------------------------------------------------
# RuntimeEvent Model Tests
# -----------------------------------------------------------


def test_runtime_event_timestamp_generated():
    event = RuntimeEvent(
        type=RuntimeEventType.START,
        phase_id="p1",
        thread_id="t1",
    )

    assert isinstance(event.timestamp, datetime)
    assert event.timestamp.tzinfo == timezone.utc


def test_runtime_event_is_immutable():
    event = RuntimeEvent(
        type=RuntimeEventType.START,
        phase_id="p1",
        thread_id="t1",
    )

    with pytest.raises(ValidationError):
        event.phase_id = "new"


def test_runtime_event_extra_fields_forbidden():
    with pytest.raises(Exception):
        RuntimeEvent(
            type=RuntimeEventType.START,
            phase_id="p1",
            thread_id="t1",
            unknown="bad",
        )


# -----------------------------------------------------------
# Factory Tests
# -----------------------------------------------------------


def test_factory_message_start():
    ctx = make_phase_context()

    agent_event = AgentEvent.message_start(
        entry_id="e1",
        agent_id="a1",
    )

    event = RuntimeEventFactory.create_runtime_event(agent_event, ctx)

    assert event.type == RuntimeEventType.START
    assert event.thread_id == "t1"
    assert event.phase_id == "p1"
    assert event.correlation_id == "corr-1"
    assert event.trace_id == "trace-1"
    assert event.content is None


def test_factory_message_chunk():
    ctx = make_phase_context()

    agent_event = AgentEvent.message_chunk(
        entry_id="e1",
        agent_id="a1",
        text="hi",
    )

    event = RuntimeEventFactory.create_runtime_event(agent_event, ctx)

    assert event.type == RuntimeEventType.PART
    assert event.content[0].text == "hi"


def test_factory_message_final():
    ctx = make_phase_context()

    agent_event = AgentEvent.message_final(
        entry_id="e1",
        agent_id="a1",
        content=[make_text("done")],
    )

    event = RuntimeEventFactory.create_runtime_event(agent_event, ctx)

    assert event.type == RuntimeEventType.COMPLETE
    assert event.content[0].text == "done"


def test_factory_suspend_with_token():
    ctx = make_phase_context()

    agent_event = AgentEvent.suspend(
        entry_id="e1",
        agent_id="a1",
        content=[make_text("approval required")],
    )

    event = RuntimeEventFactory.create_runtime_event(
        agent_event,
        ctx,
        resume_token="rtok",
    )

    assert event.type == RuntimeEventType.SUSPEND
    assert event.resume_token == "rtok"
    assert event.content[0].text == "approval required"


def test_factory_error_event():
    ctx = make_phase_context()

    agent_event = AgentEvent.error(
        entry_id="e1",
        agent_id="a1",
        content=[make_text("failure")],
    )

    event = RuntimeEventFactory.create_runtime_event(agent_event, ctx)

    assert event.type == RuntimeEventType.ERROR
    assert event.content[0].text == "failure"


# -----------------------------------------------------------
# Unknown AgentEventType
# -----------------------------------------------------------


def test_factory_unknown_event_returns_none():
    ctx = make_phase_context()

    class FakeEvent:
        type = "UNKNOWN"

    result = RuntimeEventFactory.create_runtime_event(FakeEvent(), ctx)

    assert result is None
