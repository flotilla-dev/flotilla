import pytest
import asyncio

from flotilla.agents.flotilla_agent import FlotillaAgent
from flotilla.core.thread_context import ThreadContext
from flotilla.core.thread_entries import UserInput
from flotilla.core.agent_event import AgentEvent, MessageRole
from flotilla.core.content_part import TextPart
from flotilla.core.execution_config import ExecutionConfig


def make_text(text: str):
    return TextPart(type="text", text=text)


class DummyAgent(FlotillaAgent):
    async def _execute(self, thread, config):
        yield AgentEvent.message_final(
            MessageRole.AGENT,
            "m1",
            content=[make_text("hello")],
        )


@pytest.mark.asyncio
async def test_thread_id_mismatch_rejected():
    entry = UserInput(thread_id="t1", content=[make_text("hi")])
    ctx = ThreadContext(entries=[entry])
    config = ExecutionConfig(thread_id="t2")

    agent = DummyAgent()

    with pytest.raises(Exception):
        async for _ in agent.run(ctx, config):
            pass


@pytest.mark.asyncio
async def test_agent_emits_events():
    entry = UserInput(thread_id="t1", content=[make_text("hi")])
    ctx = ThreadContext(entries=[entry])
    config = ExecutionConfig(thread_id="t1")

    agent = DummyAgent()
    events = []

    async for event in agent.run(ctx, config):
        events.append(event)

    assert len(events) == 1
    assert events[0].type.value == "message_final"


@pytest.mark.asyncio
async def test_invalid_event_rejected():
    class BadAgent(FlotillaAgent):
        async def _execute(self, thread, config):
            yield AgentEvent.message_start(
                MessageRole.AGENT,
                "m1",
            )

    entry = UserInput(thread_id="t1", content=[make_text("hi")])
    ctx = ThreadContext(entries=[entry])
    config = ExecutionConfig(thread_id="t1")

    agent = BadAgent()

    with pytest.raises(Exception):
        async for _ in agent.run(ctx, config):
            pass
