from typing import List

from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.chat_models import BaseChatModel
from langgraph.types import Checkpointer

from flotilla_langchain.agents.langchain_agent import LangChainAgent
from flotilla.tools.flotilla_tool import FlotillaTool


class ApprovalAgent(LangChainAgent):
    def __init__(self, *, llm: BaseChatModel, checkpointer: Checkpointer, tools: List[FlotillaTool]):
        super().__init__(
            agent_name="Loan Approval Agent",
            system_prompt=self.agent_prompt,
            llm=llm,
            checkpointer=checkpointer,
            tools=tools,
            middleware=[
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        "loan_processing_tool": {
                            "allowed_decisions": ["approve", "reject"],
                            "description": "Loan processing requires human approval before the loan can be finalized.",
                        }
                    }
                )
            ],
        )

    @property
    def agent_prompt(self) -> str:
        return """
        You are a loan processing agent.

        You MUST follow this sequence:

        1. Read the incoming loan request data.
        2. Call risk_assessment_tool using the provided loan request.
        3. Then call loan_processing_tool with the returned risk_score and risk_level.

        Important rules:
        - You are NOT the decision maker for approval or rejection.
        - Do NOT determine loan worthiness on your own.
        - Unless an explicit human approval decision is present, set status to PENDING_REVIEW.
        - A future human-in-the-loop step will make the final approval decision.

        Always use the tools. Do not skip steps.
        """
