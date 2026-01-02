from flotilla.agents.agent_registry import BusinessAgentRegistry
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.tools.tool_registry import ToolRegistry
from flotilla.agents.agent_selector import AgentSelector
from flotilla.agents.base_business_agent import BaseBusinessAgent
from typing import List, Optional, Dict
from flotilla.flotilla_configuration_error import FlotillaConfigurationError

def agent_registry_builder(*, container:FlotillaContainer, config:Optional[dict], agent_names:List[str], agent_selector:AgentSelector, tool_registry:ToolRegistry) -> BusinessAgentRegistry:
    agents:Dict[str, BaseBusinessAgent] = {}

    for agent_name in agent_names:
        # check if tool proivder exists
        if not container.exists(agent_name):
            raise FlotillaConfigurationError(f"Agent {agent_name} does not exist in FlotillaContainer")


        provider = container.get(agent_name)

        # If it's a DI provider, calling it returns the instance.
        instance = provider() if callable(provider) else provider

        if not isinstance(instance, BaseBusinessAgent):
            raise TypeError(
                f"Container attribute '{agent_name}' did not resolve to a BaseBusinessAgent "
                f"(got {type(instance).__name__})"
            )

        agents[agent_name] = instance
    
    return BusinessAgentRegistry(agents=agents, tool_registry=tool_registry, agent_selector=agent_selector)

