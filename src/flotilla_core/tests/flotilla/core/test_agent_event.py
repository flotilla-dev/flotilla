import pytest
from flotilla.core.agent_event import (
    AgentEvent,
    AgentEventType,
    MessageRole,
    TextPart,
)


def make_text(text: str):
    return TextPart(type="text", text=text)


def test_message_start_valid():
    event = AgentEvent.message_start(MessageRole.AGENT, "m1")
    assert event.type == AgentEventType.MESSAGE_START


def test_message_chunk_requires_text():
    with pytest.raises(Exception):
        AgentEvent(
            type=AgentEventType.MESSAGE_CHUNK,
            role=MessageRole.AGENT,
            message_id="m1",
        )


def test_message_final_requires_content():
    with pytest.raises(Exception):
        AgentEvent.message_final(
            MessageRole.AGENT,
            "m1",
            content=[],
        )


def test_suspend_requires_reason():
    with pytest.raises(Exception):
        AgentEvent(type=AgentEventType.SUSPEND)


def test_error_requires_message_and_recoverable():
    with pytest.raises(Exception):
        AgentEvent(type=AgentEventType.ERROR, message="boom")
