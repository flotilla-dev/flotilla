import asyncio
import pytest
from typing import List, Any

from langchain_core.messages import AIMessage, AIMessageChunk

from flotilla_langchain.agents.langchain_agent import LangChainAgent
from flotilla.core.thread_context import ThreadContext
from flotilla.core.thread_entries import UserInput, SuspendEntry
from flotilla.core.execution_config import ExecutionConfig
from flotilla.core.content_part import TextPart


# --------------------------------------------------
# Fake Graphs
# --------------------------------------------------


class FakeGraph:
    """
    Simulates LangGraph streaming contract.
    """

    def __init__(self, *, chunks: List[str] = None, final_text: str = ""):
        self._chunks = chunks or []
        self._final_text = final_text

    async def astream(self, *args, **kwargs):
        for text in self._chunks:
            await asyncio.sleep(0)
            yield ("messages", (AIMessageChunk(content=text), {}))

    async def aget_state(self, *args, **kwargs):
        return {"messages": [AIMessage(content=self._final_text)]}


class ErrorGraph(FakeGraph):
    async def astream(self, *args, **kwargs):
        raise RuntimeError("boom")


class LimitGraph(FakeGraph):
    def __init__(self):
        self.captured_limit = None

    async def astream(self, *args, recursion_limit=None, **kwargs):
        self.captured_limit = recursion_limit
        yield ("messages", (AIMessageChunk(content="done"), {}))

    async def aget_state(self, *args, **kwargs):
        return {"messages": [AIMessage(content="done")]}


class SlowGraph(FakeGraph):
    async def astream(self, *args, **kwargs):
        await asyncio.sleep(10)
        yield ("messages", (AIMessageChunk(content="never"), {}))

    async def aget_state(self, *args, **kwargs):
        return {"messages": [AIMessage(content="never")]}


# --------------------------------------------------
# Additional Fake Graphs for Expanded Coverage
# --------------------------------------------------


class AuthoritativeGraph(FakeGraph):
    """
    Streamed chunks differ from final authoritative state.
    Final state should win.
    """

    async def astream(self, *args, **kwargs):
        yield ("messages", (AIMessageChunk(content="partial"), {}))

    async def aget_state(self, *args, **kwargs):
        return {"messages": [AIMessage(content="complete")]}


class JsonGraph(FakeGraph):
    async def astream(self, *args, **kwargs):
        yield ("messages", (AIMessageChunk(content='{"foo": "bar"}'), {}))

    async def aget_state(self, *args, **kwargs):
        return {"messages": [AIMessage(content='{"foo": "bar"}')]}


class MetadataGraph(FakeGraph):
    async def astream(self, *args, **kwargs):
        yield ("messages", (AIMessageChunk(content="hi"), {"tokens": 3}))
        yield ("messages", (AIMessageChunk(content=" there"), {"tokens": 2}))

    async def aget_state(self, *args, **kwargs):
        return {"messages": [AIMessage(content="hi there")]}


class InterruptGraph(FakeGraph):
    async def astream(self, *args, **kwargs):
        yield ("updates", {"__interrupt__": {"reason": "approval_required"}})

    async def aget_state(self, *args, **kwargs):
        return {"messages": []}


class NoAIMessageGraph(FakeGraph):
    async def astream(self, *args, **kwargs):
        yield ("messages", (AIMessageChunk(content="hi"), {}))

    async def aget_state(self, *args, **kwargs):
        # No AIMessage present
        return {"messages": []}


class ResumeCaptureGraph(FakeGraph):
    def __init__(self):
        self.captured_command = None

    async def astream(self, *args, command=None, **kwargs):
        self.captured_command = command
        yield ("messages", (AIMessageChunk(content="resumed"), {}))

    async def aget_state(self, *args, **kwargs):
        return {"messages": [AIMessage(content="resumed")]}


# --------------------------------------------------
# Test Agent Wrapper
# --------------------------------------------------


class FakeLLM:
    pass


class TestAgent(LangChainAgent):
    def __init__(self, graph: Any):
        self.test_graph = graph
        super().__init__(
            agent_name="test",
            llm=FakeLLM(),
            system_prompt="test",
        )

    def _build_graph(self):
        return self.test_graph


# --------------------------------------------------
# Utilities
# --------------------------------------------------


@pytest.fixture
def thread() -> ThreadContext:
    entry = UserInput(
        thread_id="t1",
        entry_id="e1",
        content=[TextPart(text="hello")],
    )
    return ThreadContext(entries=[entry])


@pytest.fixture
def config() -> ExecutionConfig:
    return ExecutionConfig(thread_id="t1", recursion_limit=10)


# --------------------------------------------------
# Tests
# --------------------------------------------------


@pytest.mark.asyncio
async def test_emits_message_start_and_final(thread, config):
    graph = FakeGraph(chunks=["hi"], final_text="hi")
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread, config):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[1].type == "message_chunk"
    assert output[2].type == "message_final"
    assert output[2].content[0].text == "hi"


@pytest.mark.asyncio
async def test_streaming_emits_chunks_then_final(thread, config):
    graph = FakeGraph(chunks=["he", "llo"], final_text="hello")
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread, config):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[1].type == "message_chunk"
    assert output[2].type == "message_chunk"
    assert output[3].type == "message_final"

    combined = output[1].content[0].text + output[2].content[0].text
    assert combined == output[3].content[0].text


@pytest.mark.asyncio
async def test_error_emits_error_event(thread, config):
    graph = ErrorGraph()
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread, config):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[-1].type == "error"
    assert not any(e.type == "message_final" for e in output)


@pytest.mark.asyncio
async def test_empty_output_produces_empty_text_part(thread, config):
    graph = FakeGraph(chunks=[], final_text="")
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread, config):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[1].type == "message_final"
    assert output[1].content[0].text == ""


@pytest.mark.asyncio
async def test_recursion_limit_passed_to_graph(thread, config):
    graph = LimitGraph()
    agent = TestAgent(graph)

    async for _ in agent.run(thread, config):
        pass

    assert graph.captured_limit == config.recursion_limit


@pytest.mark.asyncio
async def test_cancellation_propagates(thread, config):
    graph = SlowGraph()
    agent = TestAgent(graph)

    async def consume():
        async for _ in agent.run(thread, config):
            await asyncio.sleep(0)

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.01)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_authoritative_final_state_wins(thread, config):
    graph = AuthoritativeGraph()
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread, config):
        output.append(e)

    final = next(e for e in output if e.type == "message_final")
    assert final.content[0].text == "complete"


from flotilla.core.content_part import JsonPart


@pytest.mark.asyncio
async def test_default_agent_treats_json_as_text(thread, config):
    graph = JsonGraph()
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread, config):
        output.append(e)

    final = next(e for e in output if e.type == "message_final")
    assert final.content[0].text == '{"foo": "bar"}'


@pytest.mark.asyncio
async def test_execution_metadata_aggregated(thread, config):
    graph = MetadataGraph()
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread, config):
        output.append(e)

    final = next(e for e in output if e.type == "message_final")

    assert final.execution_metadata is not None
    # You may adjust depending on how you aggregate
    assert "tokens" in final.execution_metadata


@pytest.mark.asyncio
async def test_interrupt_emits_suspend(thread, config):
    graph = InterruptGraph()
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread, config):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[1].type == "suspend"
    assert not any(e.type == "message_final" for e in output)


@pytest.mark.asyncio
async def test_no_ai_message_yields_error(thread, config):
    graph = NoAIMessageGraph()
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread, config):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[-1].type == "error"
    assert not any(e.type == "message_final" for e in output)


from flotilla.core.thread_entries import ResumeEntry


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_resume_command_passed_to_graph(config):
    user = UserInput(
        thread_id="t1",
        entry_id="e1",
        content=[TextPart(text="hello")],
    )

    suspend = SuspendEntry(
        thread_id="t1",
        entry_id="e2",
        content=[TextPart(text="need approval")],
    )

    resume = ResumeEntry(
        thread_id="t1",
        entry_id="e3",
        content=[TextPart(text="continue")],
    )

    thread = ThreadContext(entries=[user, suspend, resume])

    graph = ResumeCaptureGraph()
    agent = TestAgent(graph)

    async for _ in agent.run(thread, config):
        pass

    assert graph.captured_command is not None


@pytest.mark.asyncio
async def test_streaming_text_matches_final(thread, config):
    graph = FakeGraph(chunks=["a", "b", "c"], final_text="abc")
    agent = TestAgent(graph)

    chunks = []
    final_text = None

    async for e in agent.run(thread, config):
        if e.type == "message_chunk":
            chunks.append(e.content[0].text)
        if e.type == "message_final":
            final_text = e.content[0].text

    assert "".join(chunks) == final_text
