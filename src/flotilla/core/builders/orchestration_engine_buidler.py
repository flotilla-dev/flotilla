from flotilla.agents.agent_registry import BusinessAgentRegistry
from flotilla.tools.tool_registry import ToolRegistry
from flotilla.orchestration_engine import OrchestrationEngine


def orchestration_engine_builder(*, agent_registry:BusinessAgentRegistry, tool_registry:ToolRegistry) -> OrchestrationEngine:
    return OrchestrationEngine(agent_registry=agent_registry, tool_registry=tool_registry)