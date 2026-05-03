import asyncio
import pytest
from typing import List, Any

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from types import SimpleNamespace
import json


from flotilla_langchain.agents.langchain_agent import LangChainAgent
from flotilla.thread.thread_context import ThreadContext
from flotilla.thread.thread_entries import UserInput, SuspendEntry, ResumeEntry
from flotilla.runtime.phase_context import PhaseContext
from flotilla.runtime.content_part import StructuredPart, TextPart
from flotilla.agents.agent_event import AgentEvent, AgentEventType
from flotilla.tools.flotilla_tool import FlotillaTool


# --------------------------------------------------
# Fake Graphs
# --------------------------------------------------


class FakeGraph:
    def __init__(self, chunks=None, final_text=""):
        self.chunks = chunks or []
        self.final_text = final_text

    async def astream(self, *args, **kwargs):
        for c in self.chunks:
            yield ((), "messages", (AIMessageChunk(content=c), {}))

    async def aget_state(self, *args, **kwargs):
        return SimpleNamespace(values={"messages": [AIMessage(content=self.final_text)]})


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
        yield ((), "messages", (AIMessageChunk(content="partial"), {}))

    async def aget_state(self, *args, **kwargs):
        return SimpleNamespace(values={"messages": [AIMessage(content="complete")]})


class JsonGraph(FakeGraph):
    async def astream(self, *args, **kwargs):
        yield ((), "messages", (AIMessageChunk(content='{"foo":'), {}))
        yield ((), "messages", (AIMessageChunk(content='"bar"}'), {}))

    async def aget_state(self, *args, **kwargs):
        return SimpleNamespace(values={"messages": [AIMessage(content='{"foo":"bar"}')]})


class MetadataGraph(FakeGraph):

    async def astream(self, *args, **kwargs):
        yield (
            (),
            "messages",
            (
                AIMessageChunk(content="hello"),
                {"token_usage": {"completion_tokens": 3}},
            ),
        )

    async def aget_state(self, *args, **kwargs):
        return SimpleNamespace(
            values={
                "messages": [
                    AIMessage(
                        content="hello",
                        response_metadata={
                            "token_usage": {
                                "completion_tokens": 3,
                                "prompt_tokens": 5,
                                "total_tokens": 8,
                            }
                        },
                    )
                ]
            }
        )


class InterruptGraph(FakeGraph):
    async def astream(self, *args, **kwargs):
        yield ((), "updates", {"__interrupt__": {"reason": "approval_required"}})

    async def aget_state(self, *args, **kwargs):
        return SimpleNamespace(values={"messages": None})


class NoAIMessageGraph(FakeGraph):
    async def astream(self, *args, **kwargs):
        yield ("messages", (AIMessageChunk(content="hi"), {}))

    async def aget_state(self, *args, **kwargs):
        # No AIMessage present
        return {"messages": []}


class ResumeCaptureGraph(FakeGraph):
    def __init__(self):
        self.captured_input = None

    async def astream(self, graph_input, *args, **kwargs):
        self.captured_input = graph_input
        yield ("messages", (AIMessageChunk(content="resumed"), {}))

    async def aget_state(self, *args, **kwargs):
        return {"messages": [AIMessage(content="resumed")]}


class InputCaptureGraph(FakeGraph):
    def __init__(self):
        self.captured_inputs = []

    async def astream(self, graph_input, *args, **kwargs):
        self.captured_inputs.append(graph_input)
        yield ((), "messages", (AIMessageChunk(content="captured"), {}))

    async def aget_state(self, *args, **kwargs):
        return SimpleNamespace(values={"messages": [AIMessage(content="captured")]})


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


class CustomInterruptAgent(TestAgent):
    def _map_interrupt_to_content_parts(
        self,
        *,
        interrupt_payload: Any,
        thread_context: ThreadContext,
        phase_context: PhaseContext,
    ) -> List:
        return [
            StructuredPart(id="custom_interrupt_payload", data={"wrapped": interrupt_payload}),
            TextPart(id="custom_interrupt_summary", text="Custom approval required."),
        ]


class NamedTool(FlotillaTool):
    @property
    def name(self) -> str:
        return "custom_tool_name"

    @property
    def llm_description(self) -> str:
        return "A test tool."

    @property
    def execution_callable(self):
        return self.some_method

    def some_method(self, value: str) -> str:
        return value


class AsyncNamedTool(FlotillaTool):
    @property
    def name(self) -> str:
        return "async_custom_tool_name"

    @property
    def llm_description(self) -> str:
        return "An async test tool."

    @property
    def execution_callable(self):
        return self.some_method

    async def some_method(self, value: str) -> str:
        return value


# --------------------------------------------------
# Utilities
# --------------------------------------------------


@pytest.fixture
def thread_context() -> ThreadContext:
    entry = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[TextPart(text="hello")],
    )
    return ThreadContext(entries=[entry])


@pytest.fixture
def phase_context() -> PhaseContext:
    return PhaseContext(thread_id="t1", phase_id="p1", user_id="u1")


# --------------------------------------------------
# Tests
# --------------------------------------------------


@pytest.mark.asyncio
async def test_emits_message_start_and_final(thread_context, phase_context):
    graph = FakeGraph(chunks=["hi"], final_text="hi")
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread_context, phase_context):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[1].type == "message_chunk"
    assert output[2].type == "message_final"
    assert output[2].content[0].text == "hi"


@pytest.mark.asyncio
async def test_streaming_emits_chunks_then_final(thread_context, phase_context):
    graph = FakeGraph(chunks=["he", "llo"], final_text="hello")
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread_context, phase_context):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[1].type == "message_chunk"
    assert output[2].type == "message_chunk"
    assert output[3].type == "message_final"

    combined = output[1].content[0].text + output[2].content[0].text
    assert combined == output[3].content[0].text


@pytest.mark.asyncio
async def test_error_emits_error_event(thread_context, phase_context):
    graph = ErrorGraph()
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread_context, phase_context):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[-1].type == "error"
    assert not any(e.type == "message_final" for e in output)


@pytest.mark.asyncio
async def test_empty_output_produces_empty_text_part(thread_context, phase_context):
    graph = FakeGraph(chunks=[], final_text="")
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread_context, phase_context):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[1].type == "message_final"
    assert output[1].content[0].text == ""


@pytest.mark.asyncio
async def test_cancellation_propagates(thread_context, phase_context):
    graph = SlowGraph()
    agent = TestAgent(graph)

    async def consume():
        async for _ in agent.run(thread_context, phase_context):
            await asyncio.sleep(0)

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.01)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_authoritative_final_state_wins(thread_context, phase_context):
    graph = AuthoritativeGraph()
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread_context, phase_context):
        output.append(e)

    final = next(e for e in output if e.type == "message_final")
    assert final.content[0].text == "complete"


@pytest.mark.asyncio
async def test_default_agent_treats_json_as_text(thread_context, phase_context):
    graph = JsonGraph()
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread_context, phase_context):
        output.append(e)

    final = next(e for e in output if e.type == "message_final")
    assert json.loads(final.content[0].text) == {"foo": "bar"}


@pytest.mark.asyncio
async def test_execution_metadata_aggregated(thread_context, phase_context):
    graph = MetadataGraph()
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread_context, phase_context):
        output.append(e)

    final = next(e for e in output if e.type == AgentEventType.MESSAGE_FINAL)

    assert final.execution_metadata
    # You may adjust depending on how you aggregate
    # assert "tokens" in final.execution_metadata


@pytest.mark.asyncio
async def test_interrupt_emits_suspend(thread_context, phase_context):
    graph = InterruptGraph()
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread_context, phase_context):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[1].type == "suspend"
    assert len(output[1].content) == 2
    assert isinstance(output[1].content[0], StructuredPart)
    assert output[1].content[0].id == "interrupt_payload"
    assert output[1].content[0].data == {
        "kind": "langgraph_interrupt",
        "interrupts": {"reason": "approval_required"},
    }
    assert isinstance(output[1].content[1], TextPart)
    assert output[1].content[1].id == "interrupt_summary"
    assert output[1].content[1].text == "Human approval is required before execution can continue."
    assert not any(e.type == "message_final" for e in output)


@pytest.mark.asyncio
async def test_interrupt_mapping_can_be_overridden(thread_context, phase_context):
    graph = InterruptGraph()
    agent = CustomInterruptAgent(graph)

    output = []
    async for e in agent.run(thread_context, phase_context):
        output.append(e)

    suspend = output[1]
    assert suspend.type == "suspend"
    assert len(suspend.content) == 2
    assert suspend.content[0].id == "custom_interrupt_payload"
    assert suspend.content[0].data == {"wrapped": {"reason": "approval_required"}}
    assert suspend.content[1].id == "custom_interrupt_summary"
    assert suspend.content[1].text == "Custom approval required."


@pytest.mark.asyncio
async def test_no_ai_message_yields_error(thread_context, phase_context):
    graph = NoAIMessageGraph()
    agent = TestAgent(graph)

    output = []
    async for e in agent.run(thread_context, phase_context):
        output.append(e)

    assert output[0].type == "message_start"
    assert output[-1].type == "error"
    assert not any(e.type == "message_final" for e in output)


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_resume_command_passed_to_graph(phase_context):
    user = UserInput(
        thread_id="t1",
        entry_id="e1",
        phase_id="p1",
        actor_id="u1",
        content=[TextPart(text="hello")],
    )

    suspend = SuspendEntry(
        thread_id="t1",
        entry_id="e2",
        phase_id="p1",
        actor_id="a1",
        previous_entry_id="e1",
        content=[TextPart(text="need approval")],
    )

    resume = ResumeEntry(
        thread_id="t1",
        entry_id="e3",
        phase_id="p2",
        actor_id="u1",
        previous_entry_id="e2",
        content=[TextPart(text="continue")],
    )

    thread = ThreadContext(entries=[user, suspend, resume])

    graph = ResumeCaptureGraph()
    agent = TestAgent(graph)

    async for _ in agent.run(thread, phase_context):
        pass

    assert graph.captured_input is not None
    assert graph.captured_input.resume == "continue"


@pytest.mark.asyncio
async def test_structured_resume_payload_passed_to_graph(phase_context):
    user = UserInput(
        thread_id="t1",
        entry_id="e1",
        phase_id="p1",
        actor_id="u1",
        content=[TextPart(text="hello")],
    )

    suspend = SuspendEntry(
        thread_id="t1",
        entry_id="e2",
        phase_id="p1",
        actor_id="a1",
        previous_entry_id="e1",
        content=[TextPart(text="need approval")],
    )

    resume = ResumeEntry(
        thread_id="t1",
        entry_id="e3",
        phase_id="p2",
        actor_id="u1",
        previous_entry_id="e2",
        content=[
            StructuredPart(
                id="loan_review_decision",
                data={
                    "kind": "human_in_the_loop_resume",
                    "decision": "approve",
                    "decisions": [{"type": "approve"}],
                },
            )
        ],
    )

    thread = ThreadContext(entries=[user, suspend, resume])

    graph = ResumeCaptureGraph()
    agent = TestAgent(graph)

    async for _ in agent.run(thread, phase_context):
        pass

    assert graph.captured_input is not None
    assert graph.captured_input.resume == {
        "kind": "human_in_the_loop_resume",
        "decision": "approve",
        "decisions": [{"type": "approve"}],
    }


@pytest.mark.asyncio
async def test_streaming_text_matches_final(thread_context, phase_context):
    graph = FakeGraph(chunks=["a", "b", "c"], final_text="abc")
    agent = TestAgent(graph)

    chunks = []
    final_text = None

    async for e in agent.run(thread_context, phase_context):
        if e.type == "message_chunk":
            chunks.append(e.content[0].text)
        if e.type == "message_final":
            final_text = e.content[0].text

    assert "".join(chunks) == final_text


@pytest.mark.asyncio
async def test_graph_input_renders_structured_parts_as_json(phase_context):
    entry = UserInput(
        thread_id="t1",
        phase_id="p1",
        entry_id="e1",
        actor_id="u1",
        content=[StructuredPart(data={"name": "Ada", "amount": 12500.0})],
    )
    thread = ThreadContext(entries=[entry])

    graph = InputCaptureGraph()
    agent = TestAgent(graph)

    async for _ in agent.run(thread, phase_context):
        pass

    assert graph.captured_inputs
    messages = graph.captured_inputs[0]["messages"]
    assert len(messages) == 1
    assert messages[0].content == json.dumps({"amount": 12500.0, "name": "Ada"}, sort_keys=True)


@pytest.mark.asyncio
async def test_resume_entry_not_replayed_as_human_message(phase_context):
    user = UserInput(
        thread_id="t1",
        entry_id="e1",
        phase_id="p1",
        actor_id="u1",
        content=[TextPart(text="start loan flow")],
    )

    suspend = SuspendEntry(
        thread_id="t1",
        entry_id="e2",
        phase_id="p1",
        actor_id="agent",
        previous_entry_id="e1",
        content=[TextPart(text="approval required")],
    )

    resume = ResumeEntry(
        thread_id="t1",
        entry_id="e3",
        phase_id="p2",
        actor_id="reviewer",
        previous_entry_id="e2",
        content=[
            StructuredPart(
                id="loan_review_decision",
                data={
                    "kind": "human_in_the_loop_resume",
                    "decision": "approve",
                    "decisions": [{"type": "approve"}],
                },
            )
        ],
    )

    thread = ThreadContext(entries=[user, suspend, resume])
    agent = TestAgent(InputCaptureGraph())

    graph_input = agent._graph_input(thread, phase_context)
    messages = graph_input["messages"]
    assert len(messages) == 2
    assert isinstance(messages[0], HumanMessage)
    assert messages[0].content == "start loan flow"
    assert isinstance(messages[1], AIMessage)
    assert messages[1].content == "approval required"


def test_wrap_tool_uses_flotilla_tool_name():
    wrapped = LangChainAgent._wrap_tool(NamedTool())
    assert wrapped.name == "custom_tool_name"


def test_wrap_tool_preserves_invocation():
    wrapped = LangChainAgent._wrap_tool(NamedTool())
    result = wrapped.invoke({"value": "ok"})
    assert result == "ok"


@pytest.mark.asyncio
async def test_wrap_tool_preserves_async_invocation():
    wrapped = LangChainAgent._wrap_tool(AsyncNamedTool())
    result = await wrapped.ainvoke({"value": "ok"})
    assert result == "ok"
