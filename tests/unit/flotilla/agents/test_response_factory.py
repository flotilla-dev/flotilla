import json
from langchain.messages import AIMessage

from flotilla.agents.response_factory import ResponseFactory
from flotilla.agents.business_agent_response import (
    BusinessAgentResponse,
    ResponseStatus,
    ErrorResponse,
)


def test_build_success_response():
    """Ensure success response is built correctly"""
    raw = {
        "status": "success",
        "agent_name": "WeatherAgent",
        "query": "what is tomorrow's forecast for Chicago?",
        "message": "I've got the forecast ready for Chicago tomorrow! Looks like it's going to be a *partly cloudy* kind of day – I'd say the conditions are looking *un-*beleafable! Let me fetch the detailed forecast for you.",
        "confidence": 0.85,
        "data": {},
        "actions": [
            {
            "action_type": "call_tool",
            "description": "Fetch weather forecast for Chicago for tomorrow",
            "payload": {
                "tool_name": "get_weather_for_location",
                "arguments": {
                "location": "Chicago, Illinois",
                "forecast_date": "tomorrow"
                }
            }
            }
        ],
        "reasoning": "",
        "errors": []
        }
    
    json_str = json.dumps(raw)
    
    response = ResponseFactory.parse_llm_response(
        query = "test query",
        agent_name="test_agent",
        llm_response = json_str
    )

    assert isinstance(response, BusinessAgentResponse)
    assert response.status == ResponseStatus.SUCCESS
    assert response.agent_name == "WeatherAgent"
    assert response.query == "what is tomorrow's forecast for Chicago?"
    assert response.data == {}
    assert response.message == "I've got the forecast ready for Chicago tomorrow! Looks like it's going to be a *partly cloudy* kind of day – I'd say the conditions are looking *un-*beleafable! Let me fetch the detailed forecast for you."
    assert response.confidence == 0.85
    assert response.actions is not None
    assert len(response.errors) == 0



def test_parse_llm_response_with_invalid_json_returns_error():
    response = ResponseFactory.parse_llm_response(
        query="test query",
        agent_name="mock_agent",
        llm_response="{ this is not valid json"
    )

    assert isinstance(response, BusinessAgentResponse)
    assert response.status == ResponseStatus.LLM_OUTPUT_ERROR
    assert response.query == "test query"
    assert len(response.errors) == 1
    assert response.errors[0].error_code == "LLM_RESPONSE_MALFORMED"



def test_parse_llm_response_with_missing_fields_returns_error():
    raw = {
        "status": "success",
        # missing required fields like agent_name, confidence, etc.
    }

    response = ResponseFactory.parse_llm_response(
        query="test query",
        agent_name="test_agent",
        llm_response=json.dumps(raw)
    )

    assert response.status == ResponseStatus.LLM_OUTPUT_ERROR
    assert response.query == "test query"
    assert response.errors[0].error_code == "LLM_RESPONSE_MALFORMED"


def test_extract_ai_message_with_string_input():
    raw_json = json.dumps({"message": "hello"})

    result = ResponseFactory._extract_ai_message(raw_json)

    assert result == raw_json


def test_extract_ai_message_with_no_messages_returns_empty_json():
    result = ResponseFactory._extract_ai_message({})

    assert result == "{}"


def test_extract_ai_message_with_no_ai_messages_returns_empty_json():
    result = ResponseFactory._extract_ai_message({
        "messages": ["not an ai message"]
    })

    assert result == "{}"


def test_extract_ai_message_with_json_string_content():
    ai = AIMessage(content=json.dumps({"foo": "bar"}))

    result = ResponseFactory._extract_ai_message({
        "messages": [ai]
    })

    assert json.loads(result) == {"foo": "bar"}


def test_parse_llm_response_with_non_json_ai_message_returns_error():
    ai = AIMessage(content="hello world")  # violates system prompt

    response = ResponseFactory.parse_llm_response(
        query="test query",
        agent_name="test_agent",
        llm_response={"messages": [ai]}
    )

    assert response.status == ResponseStatus.LLM_OUTPUT_ERROR
    assert response.query == "test query"
    assert len(response.errors) == 1
    assert response.errors[0].error_code == "LLM_RESPONSE_MALFORMED"





def test_build_error_response_sets_required_fields():
    response = ResponseFactory.build_error_response(
        status=ResponseStatus.INTERNAL_ERROR,
        agent_name="TestAgent",
        query="test query",
        message="error occurred",
        errors=[ErrorResponse(error_code="ERR", error_details="details")]
    )

    assert response.status == ResponseStatus.INTERNAL_ERROR
    assert response.agent_name == "TestAgent"
    assert response.query == "test query"
    assert response.confidence == 0
    assert response.data == {}
    assert response.actions == []

