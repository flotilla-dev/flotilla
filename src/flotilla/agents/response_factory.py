from flotilla.agents.business_agent_response import BusinessAgentResponse, ErrorResponse, ResponseStatus
from langchain.messages import AIMessage

from typing import Any, List
import json


class ResponseFactory:

    # -----------------------------------------------------------------------
    # Response Builders
    # -----------------------------------------------------------------------
    @staticmethod
    def parse_llm_response(query:str,  llm_response:Any) -> BusinessAgentResponse:
        """
        Builds a BusinessAgentResponse from the LLM response JSON.  If the JSON is parsable
        then all vales in the response are mapped directly to thier corresponding fields
        on the BusinessAgentResponse.  

        If there is a problem parsing the JSON or mapping to the response object then a 
        BusinessAgentResponse with status of ResponseStatus.LLM_OUTPUT_ERROR is returned.

        Args:
            query - The query for this LLM response
            llm_response - The LLM response to parse
        
        Returns:
            A valid BusinessAgentResponse 

        """
        try :
            json_str = ResponseFactory._extract_ai_message(llm_response)
            agent_json = json.loads(json_str)
            return BusinessAgentResponse(
                status=agent_json["status"],
                query=agent_json["query"],
                agent_name=agent_json["agent_name"],
                confidence=agent_json["confidence"],
                message=agent_json["message"],
                reasoning=agent_json["reasoning"],
                data=agent_json["data"],
                actions=agent_json["actions"],
                errors=agent_json["errors"]
            )
        except Exception as e:
            return ResponseFactory.build_error_response(
                ResponseStatus.LLM_OUTPUT_ERROR,
                query=query,
                message="Error parsing LLM response",
                errors=[ErrorResponse(error_code="LLM_RESPONSE_MALFORMED", error_details=str(e))]         
            )
    

    @staticmethod
    def _extract_ai_message(result: Any) -> str:
        """
        Safely extract the final AIMessage from a LangChain agent.invoke() result
        and return its content as a JSON string.

        If no AIMessage is found, returns "{}".
        """
        if isinstance(result, str):
            return result
        
        if not isinstance(result, dict):
            return "{}"

        messages = result.get("messages", [])
        if not isinstance(messages, list):
            return "{}"

        # Find the last AIMessage in the list
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]
        if not ai_messages:
            return "{}"

        last_ai: AIMessage = ai_messages[-1]

        # AIMessage.content may be str OR list[BaseMessageContent]
        content = last_ai.content

        # Normalize content into a JSON-serializable value
        try:
            if isinstance(content, str):
                # If it's already JSON, keep it; otherwise wrap it
                try:
                    parsed = json.loads(content)
                    return json.dumps(parsed)
                except json.JSONDecodeError:
                    return json.dumps({"message": content})

            # If content is structured (list of parts)
            else:
                return json.dumps(content)

        except Exception:
            return "{}"

    
    @staticmethod
    def build_error_response(status:ResponseStatus, query:str, agent_name:str, message:str, errors:List[ErrorResponse] ) -> BusinessAgentResponse:
        """
        Function to build a valid BusinessAgentResponse when an exception occurs while calling the LLM

        Args:
            status - The ResponseStatus value for the response
            query - The query that processed by the LLM 
            message = The message for the user
            errors - A list of ErrorResponse objects
        
        Returns:
            A valid BusinessAgentResponse that encapsulates the error state of the application
        """
        return BusinessAgentResponse(
            status=status,
            query=query,
            agent_name=agent_name,
            confidence=0,
            message=message,
            data={},
            actions=[],
            errors=errors
        )