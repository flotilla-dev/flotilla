import pytest
from unittest.mock import Mock

from flotilla.core.runtimes.single_agent_runtime import SingleAgentRuntime
from flotilla.agents.business_agent_response import (
    BusinessAgentResponse,
    ResponseStatus,
    ErrorResponse,
)
from flotilla.core.agent_input import AgentInput
from flotilla.core.execution_config import ExecutionConfig
from flotilla.core.execution_checkpoint import ExecutionCheckpoint
from flotilla.core.runtime_event_type import RuntimeEventType
from flotilla.core.runtime_result import RuntimeResult, ResultStatus


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------


@pytest.fixture
def agent_input():
    return AgentInput(query="test query")


@pytest.fixture
def execution_config():
    return ExecutionConfig()


@pytest.fixture
def checkpoint():
    return ExecutionCheckpoint(
        execution_id="exec-1",
        payload={"step": "paused"},
        version=1,
    )


@pytest.fixture
def mock_agent():
    agent = Mock()
    agent.get_name.return_value = "test_agent"
    return agent


@pytest.fixture
def runtime(mock_agent):
    return SingleAgentRuntime(agent=mock_agent)


# -------------------------------------------------------------------
# stream() tests
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_success(runtime, mock_agent, agent_input, execution_config):
    mock_agent.run.return_value = BusinessAgentResponse(
        status=ResponseStatus.SUCCESS,
        agent_name="test_agent",
        message="done",
        data={"result": 42},
        confidence=0.9,
        query=agent_input.query,
    )

    events = []
    async for event in runtime.stream(
        agent_input=agent_input,
        execution_config=execution_config,
    ):
        events.append(event)

    assert len(events) == 2

    assert events[0].type == RuntimeEventType.START
    assert events[0].agent_name == "test_agent"

    assert events[1].type == RuntimeEventType.COMPLETE
    assert events[1].payload == {"result": 42}
    assert events[1].agent_name == "test_agent"


@pytest.mark.asyncio
async def test_stream_needs_input(
    runtime, mock_agent, agent_input, execution_config, checkpoint
):
    mock_agent.run.return_value = BusinessAgentResponse(
        status=ResponseStatus.NEEDS_INPUT,
        agent_name="test_agent",
        message="need confirmation",
        actions=[{"type": "confirm"}],
        data={"foo": "bar"},
        confidence=0.9,
        query=agent_input.query,
    )

    events = []
    async for event in runtime.stream(
        agent_input=agent_input,
        execution_config=execution_config,
    ):
        events.append(event)

    assert len(events) == 2

    assert events[0].type == RuntimeEventType.START

    await_event = events[1]
    assert await_event.type == RuntimeEventType.AWAIT_INPUT
    assert await_event.payload["message"] == "need confirmation"
    assert await_event.payload["actions"] == [{"type": "confirm"}]
    assert await_event.payload["data"] == {"foo": "bar"}
    assert await_event.agent_name == "test_agent"


@pytest.mark.asyncio
async def test_stream_error_status(runtime, mock_agent, agent_input, execution_config):
    mock_agent.run.return_value = BusinessAgentResponse(
        status=ResponseStatus.ERROR,
        agent_name="test_agent",
        message="boom",
        errors=[ErrorResponse(error_code="failure", error_details="something failed")],
        confidence=0.9,
        query=agent_input.query,
    )

    events = []
    async for event in runtime.stream(
        agent_input=agent_input,
        execution_config=execution_config,
    ):
        events.append(event)

    assert len(events) == 2
    assert events[1].type == RuntimeEventType.ERROR
    assert events[1].payload["message"] == "boom"
    assert events[1].payload["errors"] is not None


@pytest.mark.asyncio
async def test_stream_exception(runtime, mock_agent, agent_input, execution_config):
    mock_agent.run.side_effect = RuntimeError("kaboom")

    events = []
    async for event in runtime.stream(
        agent_input=agent_input,
        execution_config=execution_config,
    ):
        events.append(event)

    assert len(events) == 2
    assert events[1].type == RuntimeEventType.ERROR
    assert "kaboom" in events[1].payload["error"]


# -------------------------------------------------------------------
# run() tests
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_success(runtime, mock_agent, agent_input, execution_config):
    mock_agent.run.return_value = BusinessAgentResponse(
        status=ResponseStatus.SUCCESS,
        agent_name="test_agent",
        data={"value": 123},
        confidence=0.9,
        query=agent_input.query,
    )

    result = await runtime.run(
        agent_input=agent_input,
        execution_config=execution_config,
    )

    assert isinstance(result, RuntimeResult)
    assert result.status == ResultStatus.SUCCESS
    assert result.output == {"value": 123}
    assert result.agent_name == "test_agent"
    assert result.checkpoint is None


@pytest.mark.asyncio
async def test_run_needs_input(
    runtime, mock_agent, agent_input, execution_config, checkpoint
):
    mock_agent.run.return_value = BusinessAgentResponse(
        status=ResponseStatus.NEEDS_INPUT,
        agent_name="test_agent",
        message="approve?",
        actions=[],
        data={},
        query=agent_input.query,
        confidence=0.9,
    )

    result = await runtime.run(
        agent_input=agent_input,
        execution_config=execution_config,
    )

    assert result.status == ResultStatus.AWAITING_INPUT
    assert result.output["message"] == "approve?"
    assert result.agent_name == "test_agent"


@pytest.mark.asyncio
async def test_run_error(runtime, mock_agent, agent_input, execution_config):
    mock_agent.run.return_value = BusinessAgentResponse(
        status=ResponseStatus.ERROR,
        agent_name="test_agent",
        message="fail",
        errors=[ErrorResponse(error_code="failure", error_details="something failed")],
        query=agent_input.query,
        confidence=0.9,
    )

    result = await runtime.run(
        agent_input=agent_input,
        execution_config=execution_config,
    )

    assert result.status == ResultStatus.ERROR
    assert "message" in result.output
    assert result.agent_name == "test_agent"
