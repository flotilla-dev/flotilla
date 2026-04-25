from langchain.agents.middleware import HumanInTheLoopMiddleware

from loan_server.approval_agent import ApprovalAgent


class FakeLLM:
    pass


class FakeCheckpointer:
    pass


def test_approval_agent_uses_standard_hitl_middleware():
    agent = ApprovalAgent(
        llm=FakeLLM(),
        checkpointer=FakeCheckpointer(),
        tools=[],
    )

    assert len(agent._middleware) == 1
    middleware = agent._middleware[0]
    assert isinstance(middleware, HumanInTheLoopMiddleware)
    assert middleware.interrupt_on["loan_processing_tool"]["allowed_decisions"] == ["approve", "reject"]
