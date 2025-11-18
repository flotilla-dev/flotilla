import pytest
from pydantic import ValidationError

from agents.business_agent_response import (
    BusinessAgentResponse,
    ErrorResponse,
    ResponseStatus
)


def test_business_agent_response_success():
    """Basic success-case creation works and fields are set properly."""
    resp = BusinessAgentResponse(
        status=ResponseStatus.SUCCESS,
        agent_name="WeatherAgent",
        query="What's the weather?",
        confidence=0.85,
        message="Fetched weather",
        data={"temp_f": 72},
        actions=[{"next": "complete"}],
    )

    assert resp.status == ResponseStatus.SUCCESS
    assert resp.agent_name == "WeatherAgent"
    assert resp.query == "What's the weather?"
    assert resp.confidence == 0.85
    assert resp.data == {"temp_f": 72}
    assert resp.actions == [{"next": "complete"}]
    assert resp.errors is None


def test_business_agent_response_with_errors():
    """Ensure errors can be passed and validated."""
    err = ErrorResponse(
        error_code="API_TIMEOUT",
        error_details={"timeout": 15}
    )

    resp = BusinessAgentResponse(
        status=ResponseStatus.ERROR,
        agent_name="WeatherAgent",
        query="Weather now",
        confidence=0.0,
        message="Failed due to timeout",
        errors=[err]
    )

    assert resp.status == ResponseStatus.ERROR
    assert len(resp.errors) == 1
    assert resp.errors[0].error_code == "API_TIMEOUT"
    assert resp.errors[0].error_details == {"timeout": 15}


def test_error_response_validation():
    """Ensure ErrorResponse validates required fields."""
    with pytest.raises(ValidationError):
        ErrorResponse(error_code="MISSING_DETAILS")  # missing error_details


def test_confidence_range_validation():
    """Confidence must be between 0.0 and 1.0."""
    with pytest.raises(ValidationError):
        BusinessAgentResponse(
            status=ResponseStatus.SUCCESS,
            agent_name="Agent",
            query="test",
            confidence=1.5,  # invalid
        )

    with pytest.raises(ValidationError):
        BusinessAgentResponse(
            status=ResponseStatus.SUCCESS,
            agent_name="Agent",
            query="test",
            confidence=-0.1,  # invalid
        )


def test_status_must_be_enum():
    """Ensure status must be a valid enum value."""
    with pytest.raises(ValidationError):
        BusinessAgentResponse(
            status="stuff",  # string, not enum
            agent_name="Agent",
            query="test",
            confidence=0.9,
        )


def test_data_defaults_to_empty_dict():
    """Data field should default to an empty dict when not provided."""
    resp = BusinessAgentResponse(
        status=ResponseStatus.SUCCESS,
        agent_name="Agent",
        query="hello",
        confidence=0.75,
    )
    assert resp.data == {}


def test_actions_optional():
    """Actions should be None by default."""
    resp = BusinessAgentResponse(
        status=ResponseStatus.SUCCESS,
        agent_name="Agent",
        query="hello",
        confidence=0.75,
    )
    assert resp.actions is None
