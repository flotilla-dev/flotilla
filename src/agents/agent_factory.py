from typing import Dict, Any
import json
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool
from langchain_core.runnables import RunnableLambda, Runnable

logger = logging.getLogger("AgentFactory")


class AgentFactory:
    """
    Not currently in use, but example of how to directly create graphs in Langgraph directly if needed in the future
    """
    @staticmethod
    def create_stateless_business_agent(
        llm,
        system_prompt: str,
        domain_prompt: str,
        tools: Dict[str, StructuredTool],
        *,
        debug: bool = False,
        validate_schema: bool = True
    ) -> Runnable:
        """
        Build a fully stateless agent graph:

        Step 1: LLM receives system + domain prompt and user input → returns {"actions": [...]}
        Step 2: Tools execute
        Step 3: LLM produces final JSON with message/data/etc.

        Enhancements:
        - Debug logging
        - Schema validation
        - Better error messages
        - Deterministic casing
        - Fail-safe tool execution
        """

        # -----------------------------------------------------------
        # 1. Build the prompt
        # -----------------------------------------------------------
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("system", domain_prompt),
            ("human", "{input}")
        ])

        # LLM step
        llm_step = prompt | llm

        # -----------------------------------------------------------
        # Validation helper
        # -----------------------------------------------------------
        def validate_llm_action_output(output: Dict[str, Any], stage: str):
            if not isinstance(output, dict):
                raise ValueError(
                    f"[AgentFactory] LLM output at stage '{stage}' must be a dict, got: {type(output)}"
                )

            # Minimal check that "actions" is present for the action stage
            if stage == "actions" and "actions" not in output:
                if debug:
                    logger.warning(f"[AgentFactory] LLM output missing 'actions': {output}")

        # -----------------------------------------------------------
        # 2. Tool execution step
        # -----------------------------------------------------------
        def run_tools(ai_msg_or_dict):

            # Step 1 — Normalize: convert AIMessage → dict
            if hasattr(ai_msg_or_dict, "content"):  # AIMessage
                raw = ai_msg_or_dict.content
                if isinstance(raw, str):
                    llm_response = json.loads(raw)
                else:
                    raise ValueError("LLM must return JSON string in AIMessage.content")
            elif isinstance(ai_msg_or_dict, dict):
                # Already normalized during some tests
                llm_response = ai_msg_or_dict
            else:
                raise ValueError(f"Unexpected input to tool runner: {type(ai_msg_or_dict)}")

            # Step 2 — Validate structure
            validate_llm_action_output(llm_response, "actions")

            # Step 3 — Execute tools
            tool_outputs = {}
            actions = llm_response.get("actions", [])

            for action in actions:
                if action.get("action_type") != "call_tool":
                    continue

                payload = action.get("payload", {})
                tool_name = payload.get("tool_name")
                arguments = payload.get("arguments", {})

                tool = tools.get(tool_name)
                if tool is None:
                    tool_outputs[tool_name] = {"error": f"Tool '{tool_name}' not found"}
                else:
                    tool_outputs[tool_name] = tool.run(**arguments)

            return {
                "llm_response": llm_response,
                "tool_outputs": tool_outputs
                }

        tool_node = RunnableLambda(run_tools)

        # -----------------------------------------------------------
        # 3. Final LLM step — generate final JSON
        # -----------------------------------------------------------
        def final_step(inputs: Dict[str, Any]):
            llm_response = inputs["llm_response"]
            tool_outputs = inputs["tool_outputs"]

            if debug:
                logger.info(f"[AgentFactory] Finalizing with tool outputs:\n{json.dumps(tool_outputs, indent=2)}")

            final_prompt = (
                "You MUST output strictly valid JSON matching the business agent schema.\n"
                "Use ONLY values from:\n"
                f"LLM_RESPONSE:\n{llm_response}\n\n"
                f"TOOL_OUTPUTS:\n{tool_outputs}\n\n"
                "Fill the 'data' field with structured information from the tools.\n"
                "Fill the 'message' field with a human explanation.\n"
                "Never repeat the tool call. Never output raw tool JSON.\n"
            )

            return llm.invoke([HumanMessage(content=final_prompt)])

        final_node = RunnableLambda(final_step)

        # Final graph
        graph = llm_step | tool_node | final_node
        return graph
