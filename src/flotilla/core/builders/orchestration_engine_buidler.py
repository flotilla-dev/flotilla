from flotilla.agents.agent_registry import BusinessAgentRegistry
from flotilla.tools.tool_registry import ToolRegistry
from flotilla.core.flotilla_runtime import FlotillaRuntime


def orchestration_engine_builder(*, agent_registry:BusinessAgentRegistry, tool_registry:ToolRegistry) -> FlotillaRuntime:
    return FlotillaRuntime(agent_registry=agent_registry, tool_registry=tool_registry)