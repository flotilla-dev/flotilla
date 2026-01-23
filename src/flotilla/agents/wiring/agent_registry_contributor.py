from flotilla.container.base_contributors import GroupedContributor
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.core.errors import FlotillaConfigurationError
from flotilla.agents.wiring.agent_context import AgentContext
from flotilla.agents.builders.agent_registry_builder import agent_registry_builder

class AgentRegistryContributor(GroupedContributor):
    name = "Agent Registry Contributor"
    priority = 51

    def contribute(self, container:FlotillaContainer, context:AgentContext):        
        tool_registry = container.get("tool_registry")
        agent_selector = container.get("agent_selector")

        container.wire_infrastructure(
            name="agent_registry",
            builder=agent_registry_builder,
            container=container,
            agent_names=context.agent_names,
            tool_registry=tool_registry,
            agent_selector=agent_selector
            )

    
    def validate(self, container: FlotillaContainer, context: AgentContext):
        if not container.exists("agent_registry"):
            #raise an error
            raise FlotillaConfigurationError("AgentRegistry configuration failed validation")