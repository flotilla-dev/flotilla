import pytest
from unittest.mock import MagicMock

from flotilla.core.flotilla_runtime import FlotillaRuntime
from flotilla.agents.business_agent_response import (
    BusinessAgentResponse,
    ResponseStatus,
    ErrorResponse,
)

@pytest.fixture
def mock_agent_registry():
    return MagicMock()

@pytest.fixture
def mock_tool_registry():
    return MagicMock()

@pytest.mark.unit

def test_constructor_starts_agent_registry(
    mock_agent_registry,
    mock_tool_registry
):
    """Engine constructor should start the agent registry"""
    mock_agent_registry.start = MagicMock()

    engine = FlotillaRuntime(
        agent_registry=mock_agent_registry,
        tool_registry=mock_tool_registry
    )

    assert engine.running is True
    mock_agent_registry.start.assert_called_once()


def test_run_executes_selected_agent(
    mock_agent_registry,
    mock_tool_registry
):
    """Runtime should select and execute an agent"""
    mock_agent_registry.start = MagicMock()

    mock_agent = MagicMock()
    mock_response = MagicMock(spec=BusinessAgentResponse)

    mock_agent.agent_name = "TestAgent"
    mock_agent.run.return_value = mock_response
    mock_agent_registry.select_agent.return_value = mock_agent

    engine = FlotillaRuntime(
        agent_registry=mock_agent_registry,
        tool_registry=mock_tool_registry
    )

    response = engine.run(
        query="test query",
        user_id="user-1",
        thread_id="thread-1",
        request_id="trace-1",
        metadata={"foo": "bar"}
    )

    assert response == mock_response
    mock_agent_registry.select_agent.assert_called_once()
    mock_agent.run.assert_called_once()



def test_run_passes_correct_agent_input(
    mock_agent_registry,
    mock_tool_registry
):
    """AgentInput should be constructed correctly"""
    mock_agent_registry.start = MagicMock()

    mock_agent = MagicMock()
    mock_agent.agent_name = "TestAgent"
    mock_agent.run.return_value = MagicMock()

    mock_agent_registry.select_agent.return_value = mock_agent

    engine = FlotillaRuntime(
        agent_registry=mock_agent_registry,
        tool_registry=mock_tool_registry
    )

    engine.run(
        query="hello",
        user_id="u1",
        thread_id="t1",
        metadata={"k": "v"}
    )

    agent_input = mock_agent_registry.select_agent.call_args.kwargs["agent_input"]

    assert agent_input.query == "hello"
    assert agent_input.user_id == "u1"
    assert agent_input.thread_id == "t1"
    assert agent_input.metadata == {"k": "v"}



def test_run_passes_execution_config(
    mock_agent_registry,
    mock_tool_registry
):
    """ExecutionConfig should be wired correctly"""
    mock_agent_registry.start = MagicMock()

    mock_agent = MagicMock()
    mock_agent.agent_name = "TestAgent"
    mock_agent.run.return_value = MagicMock()

    mock_agent_registry.select_agent.return_value = mock_agent

    engine = FlotillaRuntime(
        agent_registry=mock_agent_registry,
        tool_registry=mock_tool_registry
    )

    engine.run(
        query="hello",
        thread_id="thread-123",
        request_id="trace-abc"
    )

    _, kwargs = mock_agent.run.call_args
    config = kwargs["config"]

    assert config.thread_id == "thread-123"
    assert config.trace_id == "trace-abc"



def test_run_returns_error_when_no_agent_found(
    mock_agent_registry,
    mock_tool_registry
):
    """No agent selected should return NO_VALID_AGENT response"""
    mock_agent_registry.start = MagicMock()
    mock_agent_registry.select_agent.return_value = None

    engine = FlotillaRuntime(
        agent_registry=mock_agent_registry,
        tool_registry=mock_tool_registry
    )

    response = engine.run(query="unknown query")

    assert response.status == ResponseStatus.NO_VALID_AGENT
    assert isinstance(response.errors[0], ErrorResponse)
    assert response.errors[0].error_code == "NO_VALID_AGENT"



def test_run_does_not_execute_agent_if_none_selected(
    mock_agent_registry,
    mock_tool_registry
):
    mock_agent_registry.start = MagicMock()
    mock_agent_registry.select_agent.return_value = None

    engine = FlotillaRuntime(
        agent_registry=mock_agent_registry,
        tool_registry=mock_tool_registry
    )

    engine.run(query="test")

    mock_agent_registry.select_agent.assert_called_once()




def test_cleanup_shuts_down_registries(
    mock_agent_registry,
    mock_tool_registry
):
    """Cleanup should shutdown tool and agent registries"""
    mock_agent_registry.start = MagicMock()
    mock_agent_registry.shutdown = MagicMock()
    mock_tool_registry.shutdown = MagicMock()

    engine = FlotillaRuntime(
        agent_registry=mock_agent_registry,
        tool_registry=mock_tool_registry
    )

    engine.cleanup()

    mock_tool_registry.shutdown.assert_called_once()
    mock_agent_registry.shutdown.assert_called_once()
    assert engine.running is False


def test_cleanup_idempotent(
    mock_agent_registry,
    mock_tool_registry
):
    """Calling cleanup twice should not double-shutdown"""
    mock_agent_registry.start = MagicMock()
    mock_agent_registry.shutdown = MagicMock()
    mock_tool_registry.shutdown = MagicMock()

    engine = FlotillaRuntime(
        agent_registry=mock_agent_registry,
        tool_registry=mock_tool_registry
    )

    engine.cleanup()
    engine.cleanup()

    mock_tool_registry.shutdown.assert_called_once()
    mock_agent_registry.shutdown.assert_called_once()
    assert engine.running is False



        
    
    
    