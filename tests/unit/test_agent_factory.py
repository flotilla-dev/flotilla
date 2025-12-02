import pytest
from typing import List, Any
from pydantic import Field
from langchain_core.messages import AIMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.tools import StructuredTool

from agents.agent_factory import AgentFactory

import json


# ============================================================
# FAKE LLM — supports dict output + AIMessage wrapping
# ============================================================
class FakeRunnableLLM(BaseChatModel):
    """
    A fake LLM for LangChain 1.x Runnable pipelines.
    Returns ChatResult(gen=[ChatGeneration(message=AIMessage(...))]).
    AIMessage.content is JSON string so AgentFactory can load it.
    """

    responses: List[Any] = Field(default_factory=list)
    history: List[Any] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fake-runnable-llm"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        # Store incoming messages for test inspection
        self.history.append(messages)

        if not self.responses:
            response = {"status": "success", "actions": []}
        else:
            response = self.responses.pop(0)

        # Produce JSON *string* so pydantic accepts AIMessage
        msg = AIMessage(content=json.dumps(response))

        # Return a ChatResult, as real LC LLMs do
        generation = ChatGeneration(message=msg)
        return ChatResult(generations=[generation])


# ============================================================
# TOOL HELPER
# ============================================================
def make_tool(name, return_value, capture=None):
    """Creates a StructuredTool whose kwargs are captured when invoked."""
    def fn(**kwargs):
        if capture is not None:
            capture["args"] = kwargs
        return return_value

    return StructuredTool.from_function(
        fn,
        name=name,
        description=f"Mock tool {name}"
    )


# ============================================================
# MESSAGE EXTRACTION HELPERS
# ============================================================
def extract_text(obj):
    """
    Convert nested LLM messages (lists, dicts, tuples) into a combined string.
    Works for any structure LangChain produces in .history.
    """
    if isinstance(obj, (list, tuple)):
        return "".join(extract_text(x) for x in obj)
    if isinstance(obj, dict):
        return "".join(extract_text(v) for v in obj.values())
    return str(obj)


# ============================================================
# TEST SUITE
# ============================================================
@pytest.mark.unit
class TestAgentFactory:

    # --------------------------------------------------------
    # 1. Agent returns a runnable
    # --------------------------------------------------------
    def test_returns_runnable(self):
        llm = FakeRunnableLLM(responses=[{"actions": []}])
        tools = {"mock": make_tool("mock", {"result": True})}

        agent = AgentFactory.create_stateless_business_agent(
            llm=llm,
            system_prompt="SYSTEM",
            domain_prompt="DOMAIN",
            tools=tools
        )

        assert hasattr(agent, "invoke"), "Agent should be runnable"


    # --------------------------------------------------------
    # 2. LLM receives system prompt, domain prompt, and user input
    # --------------------------------------------------------
    def test_llm_receives_system_domain_and_input(self):
        llm = FakeRunnableLLM(responses=[{"actions": []}])
        tools = {"mock": make_tool("mock", {"result": True})}

        agent = AgentFactory.create_stateless_business_agent(
            llm=llm,
            system_prompt="SYSTEM_PROMPT",
            domain_prompt="DOMAIN_PROMPT",
            tools=tools
        )

        agent.invoke({"input": "Hello world"})

        # FIRST CALL STORED IN llm.history[0]
        first_call = llm.history[0]
        combined = extract_text(first_call)

        assert "SYSTEM_PROMPT" in combined
        assert "DOMAIN_PROMPT" in combined
        assert "Hello world" in combined


    # --------------------------------------------------------
    # 3. Tool should be called with provided arguments
    # --------------------------------------------------------
    '''
    def test_tool_is_called(self):
        llm = FakeRunnableLLM(responses=[
            {
                "actions": [
                    {
                        "action_type": "call_tool",
                        "payload": {
                            "tool_name": "mock_tool",
                            "arguments": {"x": 123}
                        }
                    }
                ]
            },
            {"status": "success"}
        ])

        capture = {}
        tools = {"mock_tool": make_tool("mock_tool", {"ok": True}, capture)}

        agent = AgentFactory.create_stateless_business_agent(
            llm=llm,
            system_prompt="SYSTEM",
            domain_prompt="DOMAIN",
            tools=tools
        )

        agent.invoke({"input": "run tool"})

        assert capture["args"] == {"x": 123}, "Tool should be invoked with x=123"


    # --------------------------------------------------------
    # 4. Final step receives tool outputs properly
    # --------------------------------------------------------
    def test_final_step_receives_tool_outputs(self):
        llm = FakeRunnableLLM(responses=[
            # FIRST LLM CALL: choose actions
            {
                "actions": [
                    {
                        "action_type": "call_tool",
                        "payload": {
                            "tool_name": "mock_tool",
                            "arguments": {}
                        }
                    }
                ]
            },
            # SECOND LLM CALL: final output
            {
                "status": "success",
                "data": {"forecast": "sunny"}
            }
        ])

        tools = {"mock_tool": make_tool("mock_tool", {"value": "mock-return"})}

        agent = AgentFactory.create_stateless_business_agent(
            llm=llm,
            system_prompt="SYS",
            domain_prompt="DOM",
            tools=tools
        )

        result_message = agent.invoke({"input": "forecast?"})

        # result_message is an AIMessage
        assert result_message.content["status"] == "success"
        assert result_message.content["data"] == {"forecast": "sunny"}


    # --------------------------------------------------------
    # 5. Statelessness test: second call must not reuse first call's actions
    # --------------------------------------------------------
    def test_stateless_behavior(self):
        llm = FakeRunnableLLM(responses=[
            # First run
            {"actions": [
                {"action_type": "call_tool",
                 "payload": {"tool_name": "mock_tool", "arguments": {}}}
            ]},
            {"status": "success"},

            # Second run → NO actions
            {"actions": []},
            {"status": "success"}
        ])

        capture = {"count": 0}

        def counter_tool(**kwargs):
            capture["count"] += 1
            return {"ok": True}

        tools = {
            "mock_tool": StructuredTool.from_function(
                counter_tool,
                name="mock_tool",
                description="counter tool"
            )
        }

        agent = AgentFactory.create_stateless_business_agent(
            llm=llm,
            system_prompt="SYS",
            domain_prompt="DOM",
            tools=tools
        )

        # First call → tool runs
        agent.invoke({"input": "first"})
        assert capture["count"] == 1

        # Second call → tool must NOT run
        agent.invoke({"input": "second"})
        assert capture["count"] == 1, "Agent must be stateless across calls"
        '''
