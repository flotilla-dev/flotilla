from agents.response_factory import ResponseFactory
from agents.business_agent_response import BusinessAgentResponse, ResponseStatus, ErrorResponse
import json

class TestResponseFactory:
    def test_build_success_response(self):
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



    def test_build_error_reponse(self):
        response = ResponseFactory.build_error_response(
            status = ResponseStatus.INTERNAL_ERROR,
            agent_name="Test Agent",
            query = "mock query",
            message = "test error message",
            errors = [ErrorResponse(error_code="MOCK_ERROR", error_details="Error message")]
        )

        assert response is not None
        assert isinstance(response, BusinessAgentResponse)
        assert response.status == ResponseStatus.INTERNAL_ERROR
        assert response.agent_name == "Test Agent"
        assert response.query == "mock query"
        assert response.data == {}
        assert response.confidence == 0
        assert len(response.actions) == 0
        assert response.errors == [ErrorResponse(error_code="MOCK_ERROR", error_details="Error message")]
