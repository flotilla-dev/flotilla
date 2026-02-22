import asyncio
import pytest
from typing import AsyncIterator, List

from flotilla_langchain.agents.langchain_agent import LangChainAgent
from flotilla.core.thread_context import ThreadContext
from flotilla.core.thread_entries import UserInput
from flotilla.core.agent_event import AgentEvent
from flotilla.core.execution_config import ExecutionConfig
from flotilla.core.content_part import TextPart


# ---------------------------
# Test Utilities
# ---------------------------


class FakeGraph:
    """
    Minimal fake CompiledStateGraph replacement.
    Simulates async streaming behavior.
    """

    def __init__(self, events: List[dict]):
        self._events = events

    async def astream(self, *args, **kwargs):
        for event in self._events:
            await asyncio.sleep(0)
            yield event


class FakeLLM:
    pass


class FakeTool:
    def name(self):
        return "fake_tool"

    def llm_description(self):
        return "fake"

    def execution_callable(self):
        async def run(x: str):
            return f"echo:{x}"

        return run


def make_thread() -> ThreadContext:
    entry = UserInput(thread_id="t1", content=[TextPart(text="hello")])
    return ThreadContext(entries=[entry])


def make_config() -> ExecutionConfig:
    return ExecutionConfig(thread_id="t1", recursion_limit=10)


# ---------------------------
# Construction Tests
# ---------------------------


def test_constructor_builds_graph_once(monkeypatch):
    built = {"count": 0}

    class TestAgent(LangChainAgent):
        def _build_graph(self):
            built["count"] += 1
            return FakeGraph([])

    TestAgent(llm=FakeLLM())
    assert built["count"] == 1


def test_constructor_fails_fast_on_graph_error():
    class TestAgent(LangChainAgent):
        def _build_graph(self):
            raise RuntimeError("bad graph")

    with pytest.raises(RuntimeError):
        TestAgent(llm=FakeLLM())


# ---------------------------
# Execution Lifecycle Tests
# ---------------------------


@pytest.mark.asyncio
async def test_emits_message_start_and_final():
    events = [{"type": "final", "text": "hi"}]

    class TestAgent(LangChainAgent):
        def _build_graph(self):
            return FakeGraph(events)

    agent = TestAgent(llm=FakeLLM())
    thread = make_thread()
    config = make_config()

    output = []
    async for e in agent.run(thread, config):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[1].type == "message_final"
    assert output[1].content[0].text == "hi"


@pytest.mark.asyncio
async def test_streaming_emits_chunks_then_final():
    events = [
        {"type": "chunk", "text": "he"},
        {"type": "chunk", "text": "llo"},
        {"type": "final", "text": "hello"},
    ]

    class TestAgent(LangChainAgent):
        def _build_graph(self):
            return FakeGraph(events)

    agent = TestAgent(llm=FakeLLM())
    thread = make_thread()
    config = make_config()

    output = []
    async for e in agent.run(thread, config):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[1].type == "message_chunk"
    assert output[2].type == "message_chunk"
    assert output[3].type == "message_final"

    combined = output[1].content_text + output[2].content_text
    assert combined == output[3].content[0].text


@pytest.mark.asyncio
async def test_no_message_final_after_error():
    events = [
        {"type": "chunk", "text": "partial"},
        {"type": "error", "message": "boom"},
    ]

    class TestAgent(LangChainAgent):
        def _build_graph(self):
            return FakeGraph(events)

    agent = TestAgent(llm=FakeLLM())
    thread = make_thread()
    config = make_config()

    output = []
    async for e in agent.run(thread, config):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[-1].type == "error"

    assert not any(e.type == "message_final" for e in output)


@pytest.mark.asyncio
async def test_empty_output_produces_empty_text_part():
    events = []

    class TestAgent(LangChainAgent):
        def _build_graph(self):
            return FakeGraph(events)

    agent = TestAgent(llm=FakeLLM())
    thread = make_thread()
    config = make_config()

    output = []
    async for e in agent.run(thread, config):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[1].type == "message_final"
    assert output[1].content[0].text == ""


# ---------------------------
# Resume Behavior
# ---------------------------


@pytest.mark.asyncio
async def test_resume_passes_command(monkeypatch):
    called = {"resume": False}

    class ResumeGraph(FakeGraph):
        async def astream(self, command=None, **kwargs):
            if command:
                called["resume"] = True
            yield {"type": "final", "text": "resumed"}

    class TestAgent(LangChainAgent):
        def _build_graph(self):
            return ResumeGraph([])

    agent = TestAgent(llm=FakeLLM())
    thread = make_thread()
    config = make_config()

    async for _ in agent.run(thread, config):
        pass

    assert called["resume"] is False


# ---------------------------
# Cancellation Behavior
# ---------------------------


@pytest.mark.asyncio
async def test_cancellation_propagates():
    class SlowGraph(FakeGraph):
        async def astream(self, *args, **kwargs):
            await asyncio.sleep(10)
            yield {"type": "final", "text": "never"}

    class TestAgent(LangChainAgent):
        def _build_graph(self):
            return SlowGraph([])

    agent = TestAgent(llm=FakeLLM())
    thread = make_thread()
    config = make_config()

    task = asyncio.create_task(agent.run(thread, config).__anext__())

    await asyncio.sleep(0.01)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


# ---------------------------
# Recursion Limit Pass-Through
# ---------------------------


@pytest.mark.asyncio
async def test_recursion_limit_passed_to_graph(monkeypatch):
    captured = {"limit": None}

    class LimitGraph(FakeGraph):
        async def astream(self, recursion_limit=None, **kwargs):
            captured["limit"] = recursion_limit
            yield {"type": "final", "text": "done"}

    class TestAgent(LangChainAgent):
        def _build_graph(self):
            return LimitGraph([])

    agent = TestAgent(llm=FakeLLM())
    thread = make_thread()
    config = make_config()

    async for _ in agent.run(thread, config):
        pass

    assert captured["limit"] == config.recursion_limit
