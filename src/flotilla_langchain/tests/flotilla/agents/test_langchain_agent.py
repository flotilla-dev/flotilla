import asyncio
import pytest
from typing import List, Any

from langchain_core.messages import AIMessage, AIMessageChunk

from flotilla_langchain.agents.langchain_agent import LangChainAgent
from flotilla.core.thread_context import ThreadContext
from flotilla.core.thread_entries import UserInput
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
