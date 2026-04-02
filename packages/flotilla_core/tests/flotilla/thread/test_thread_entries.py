import pytest
from pydantic import ValidationError

from flotilla.thread.thread_entries import (
    ThreadEntryFactory,
    UserInput,
    AgentOutput,
    SuspendEntry,
    ResumeEntry,
    ErrorEntry,
    ClosedEntry,
    ActorType,
    ThreadEntryType,
)

from flotilla.runtime.content_part import TextPart


def make_text(text: str):
    return TextPart(type="text", text=text)


# -----------------------------
# IMMUTABILITY
# -----------------------------


def test_thread_entry_is_immutable():
    entry = UserInput(
        thread_id="t1",
        phase_id="p1",
        actor_id="u1",
        content=[make_text("hello")],
    )

    with pytest.raises(ValidationError):
        entry.thread_id = "t2"


# -----------------------------
# REQUIRED FIELDS
# -----------------------------


def test_user_input_requires_content():
    with pytest.raises(ValidationError):
        UserInput(
            thread_id="t1",
            phase_id="p1",
            actor_id="u1",
            content=[],  # invalid (min_length=1)
        )


def test_missing_required_fields():
    with pytest.raises(ValidationError):
        UserInput(
            thread_id="t1",
            # missing phase_id
            actor_id="u1",
            content=[make_text("hello")],
        )


# -----------------------------
# ACTOR VALIDATION
# -----------------------------


def test_user_input_actor_must_be_user():
    with pytest.raises(ValidationError):
        UserInput(
            thread_id="t1",
            phase_id="p1",
            actor_id="u1",
            actor_type=ActorType.AGENT,  # invalid
            content=[make_text("hello")],
        )


def test_agent_output_actor_valid():
    entry = AgentOutput(
        thread_id="t1",
        phase_id="p1",
        actor_id="a1",
        content=[make_text("hello")],
    )

    assert entry.actor_type == ActorType.AGENT


def test_terminal_allows_system_actor():
    entry = ErrorEntry(
        thread_id="t1",
        phase_id="p1",
        actor_id="sys",
        actor_type=ActorType.SYSTEM,
        content=[make_text("error")],
    )

    assert entry.actor_type == ActorType.SYSTEM


# -----------------------------
# SERIALIZATION
# -----------------------------


def test_serialize_round_trip():
    entry = AgentOutput(
        thread_id="t1",
        phase_id="p1",
        actor_id="a1",
        content=[make_text("hello")],
    )

    data = entry.serialize()

    restored = ThreadEntryFactory.deserialize_entry(data)

    assert restored == entry


def test_serialize_excludes_none():
    entry = AgentOutput(
        thread_id="t1",
        phase_id="p1",
        actor_id="a1",
        content=[make_text("hello")],
    )

    data = entry.serialize()

    assert "entry_id" not in data
    assert "timestamp" not in data


# -----------------------------
# DISCRIMINATOR / FACTORY
# -----------------------------


def test_factory_deserializes_correct_type():
    data = {
        "type": "user",
        "thread_id": "t1",
        "phase_id": "p1",
        "actor_type": "user",
        "actor_id": "u1",
        "content": [{"type": "text", "text": "hello"}],
    }

    entry = ThreadEntryFactory.deserialize_entry(data)

    assert isinstance(entry, UserInput)


def test_factory_invalid_type_fails():
    data = {
        "type": "invalid",
        "thread_id": "t1",
        "phase_id": "p1",
        "actor_type": "user",
        "actor_id": "u1",
        "content": [{"type": "text", "text": "hello"}],
    }

    with pytest.raises(ValidationError):
        ThreadEntryFactory.deserialize_entry(data)


# -----------------------------
# SUBCLASS TYPE LOCKING
# -----------------------------


def test_type_is_fixed_on_subclass():
    entry = UserInput(
        thread_id="t1",
        phase_id="p1",
        actor_id="u1",
        content=[make_text("hello")],
    )

    assert entry.type == ThreadEntryType.USER_INPUT


def test_cannot_override_type():
    with pytest.raises(ValidationError):
        UserInput(
            type="agent",  # invalid override
            thread_id="t1",
            phase_id="p1",
            actor_id="u1",
            content=[make_text("hello")],
        )
