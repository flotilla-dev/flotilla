from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import InMemorySaver

from loan_server.approval_agent import ApprovalAgent


def test_approval_agent_uses_standard_hitl_middleware():
    agent = ApprovalAgent(
        llm=FakeListChatModel(responses=["ok"]),
        checkpointer=InMemorySaver(),
        tools=[],
    )

    assert len(agent._middleware) == 1
    middleware = agent._middleware[0]
    assert isinstance(middleware, HumanInTheLoopMiddleware)
    assert middleware.interrupt_on["loan_processing_tool"]["allowed_decisions"] == ["approve", "reject"]
