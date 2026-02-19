from flotilla.core.runtimes.single_agent_runtime import SingleAgentRuntime
from flotilla.agents.base_business_agent import BaseBusinessAgent


def create_single_factory_runtime(agent: BaseBusinessAgent) -> SingleAgentRuntime:
    return SingleAgentRuntime(agent=agent)
