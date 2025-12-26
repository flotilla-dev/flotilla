import pytest
from unittest.mock import MagicMock

from flotilla.orchestration_engine import OrchestrationEngine
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
class TestOrchestrationEngine:

    def test_constructor_starts_agent_registry(
        self,
        mock_agent_registry,
        mock_tool_registry
    ):
        """Engine constructor should start the agent registry"""
        mock_agent_registry.start = MagicMock()

        engine = OrchestrationEngine(
            agent_registry=mock_agent_registry,
            tool_registry=mock_tool_registry
        )

        assert engine.running is True
        mock_agent_registry.start.assert_called_once()


    def test_execute_delegates_to_agent_registry(
        self,
        mock_agent_registry,
        mock_tool_registry
    ):
        """Execute should delegate to agent registry"""
        expected_response = BusinessAgentResponse(
            status=ResponseStatus.SUCCESS,
            query="test query",
            confidence=0.7,
            agent_name="TestAgent",
            result={"answer": "ok"}
        )

        mock_agent_registry.execute_with_best_agent = MagicMock(
            return_value=expected_response
        )
        mock_agent_registry.start = MagicMock()

        engine = OrchestrationEngine(
            agent_registry=mock_agent_registry,
            tool_registry=mock_tool_registry
        )

        response = engine.execute(
            query="test query",
            context={"foo": "bar"}
        )

        mock_agent_registry.execute_with_best_agent.assert_called_once_with(
            query="test query",
            context={"foo": "bar"}
        )
        assert response == expected_response


    def test_execute_returns_error_on_exception(self, mock_agent_registry, mock_tool_registry):
        """Engine should return error response if execution raises (regression: must return the built response)"""
        mock_agent_registry.execute_with_best_agent = MagicMock(
            side_effect=RuntimeError("boom")
        )
        mock_agent_registry.start = MagicMock()

        engine = OrchestrationEngine(
            agent_registry=mock_agent_registry,
            tool_registry=mock_tool_registry
        )

        response = engine.execute(
            query="test query",
            context={}
        )

        # This is the contract we want: always return a BusinessAgentResponse
        assert isinstance(response, BusinessAgentResponse)
        assert response.status == ResponseStatus.INTERNAL_ERROR
        assert response.query == "test query"
        assert response.agent_name == "Unknown"
        assert response.errors
        assert response.errors[0].error_code == "AGENT_EXECUTION_FAILED"
        assert "boom" in response.errors[0].error_details



    def test_cleanup_shuts_down_registries(
        self,
        mock_agent_registry,
        mock_tool_registry
    ):
        """Cleanup should shutdown tool and agent registries"""
        mock_agent_registry.start = MagicMock()
        mock_agent_registry.shutdown = MagicMock()
        mock_tool_registry.shutdown = MagicMock()

        engine = OrchestrationEngine(
            agent_registry=mock_agent_registry,
            tool_registry=mock_tool_registry
        )

        engine.cleanup()

        mock_tool_registry.shutdown.assert_called_once()
        mock_agent_registry.shutdown.assert_called_once()
        assert engine.running is False


    def test_cleanup_idempotent(
        self,
        mock_agent_registry,
        mock_tool_registry
    ):
        """Calling cleanup twice should not double-shutdown"""
        mock_agent_registry.start = MagicMock()
        mock_agent_registry.shutdown = MagicMock()
        mock_tool_registry.shutdown = MagicMock()

        engine = OrchestrationEngine(
            agent_registry=mock_agent_registry,
            tool_registry=mock_tool_registry
        )

        engine.cleanup()
        engine.cleanup()

        mock_tool_registry.shutdown.assert_called_once()
        mock_agent_registry.shutdown.assert_called_once()
        assert engine.running is False



        
    
    
    