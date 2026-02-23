import pytest

from flotilla.agents.flotilla_agent import FlotillaAgent
from flotilla.core.thread_context import ThreadContext
from flotilla.core.thread_entries import UserInput
from flotilla.core.agent_event import AgentEvent, AgentEventType
from flotilla.core.content_part import TextPart
from flotilla.core.execution_config import ExecutionConfig


# ----------------------------
# Helpers
# ----------------------------


def make_text(text: str):
    return TextPart(text=text)


# ----------------------------
# Dummy Agents
# ----------------------------


class StreamingAgent(FlotillaAgent):
    def __init__(self):
        super().__init__(agent_name="streaming agent")

    async def _execute(self, thread, config):
        entry_id = thread.entries[-1].entry_id

        yield AgentEvent.message_start(entry_id=entry_id)
        yield AgentEvent.message_chunk(entry_id=entry_id, text="hel")
        yield AgentEvent.message_chunk(entry_id=entry_id, text="lo")
        yield AgentEvent.message_final(
            entry_id=entry_id,
            content=[make_text("hello")],
        )


class MetadataAgent(FlotillaAgent):
    def __init__(self):
        super().__init__(agent_name="metadata agent")

    async def _execute(self, thread, config):
        entry_id = thread.entries[-1].entry_id

        yield AgentEvent.message_start(entry_id=entry_id)
        yield AgentEvent.message_final(
            entry_id=entry_id,
            content=[make_text("done")],
            metadata={"tokens": 42},
        )


@pytest.fixture
def mock_user_input() -> UserInput:
    return UserInput(thread_id="t1", entry_id="e1", content=[make_text("hi")])


@pytest.fixture
def mock_thread_context(mock_user_input) -> ThreadContext:
    return ThreadContext(entries=[mock_user_input])


@pytest.fixture
def mock_good_execution_config() -> ExecutionConfig:
    return ExecutionConfig(thread_id="t1")


@pytest.fixture
def mock_bad_execution_config() -> ExecutionConfig:
    return ExecutionConfig(thread_id="t2")


# ----------------------------
# Tests
# ----------------------------


@pytest.mark.asyncio
async def test_thread_id_mismatch_rejected(
    mock_thread_context, mock_bad_execution_config
):
    agent = StreamingAgent()

    with pytest.raises(Exception):
        async for _ in agent.run(mock_thread_context, mock_bad_execution_config):
            pass


@pytest.mark.asyncio
async def test_agent_emits_streaming_sequence(
    mock_user_input, mock_good_execution_config
):
    entry = mock_user_input
    ctx = ThreadContext(entries=[entry])

    agent = StreamingAgent()
    events = []

    async for event in agent.run(ctx, mock_good_execution_config):
        events.append(event)

    assert len(events) == 4

    assert events[0].type == AgentEventType.MESSAGE_START
    assert events[1].type == AgentEventType.MESSAGE_CHUNK
    assert events[2].type == AgentEventType.MESSAGE_CHUNK
    assert events[3].type == AgentEventType.MESSAGE_FINAL

    # parent_entry_id should match initiating entry
    for e in events:
        assert e.parent_entry_id == entry.entry_id

    # Streaming reconstruction check (agent-level behavior only)
    streamed_text = "".join(
        part.text
        for e in events
        if e.type == AgentEventType.MESSAGE_CHUNK
        for part in e.content
    )

    final_text = events[-1].content[0].text
    assert streamed_text == final_text


@pytest.mark.asyncio
async def test_message_final_content_structure(
    mock_thread_context, mock_good_execution_config
):
    agent = StreamingAgent()
    events = []

    async for event in agent.run(mock_thread_context, mock_good_execution_config):
        events.append(event)

    final_event = events[-1]

    assert final_event.type == AgentEventType.MESSAGE_FINAL
    assert len(final_event.content) == 1
    assert isinstance(final_event.content[0], TextPart)
    assert final_event.content[0].text == "hello"
    assert final_event.execution_metadata is None


@pytest.mark.asyncio
async def test_metadata_passthrough(mock_thread_context, mock_good_execution_config):

    agent = MetadataAgent()
    events = []

    async for event in agent.run(mock_thread_context, mock_good_execution_config):
        events.append(event)

    final_event = events[-1]

    assert final_event.type == AgentEventType.MESSAGE_FINAL
    assert final_event.execution_metadata == {"tokens": 42}
