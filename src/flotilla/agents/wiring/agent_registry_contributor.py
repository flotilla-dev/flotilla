from flotilla.container.base_contributors import WiringContributor, GroupedContributor
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.flotilla_configuration_error import FlotillaConfigurationError
from flotilla.agents.wiring.agent_context import AgentContext

class AgentRegistryContributor(GroupedContributor):
    name = "Agent Registry Contributor"
    priority = 51

    def contribute(self, container:FlotillaContainer, context:AgentContext):
        builder = container.get_builder("agent_registry")
        if not builder:
            raise FlotillaConfigurationError("AgentRegistry builder not registered")
        
        tool_registry = container.get("tool_registry")
        agent_selector = container.get("agent_selector")

        container.wire_infrastructure(
            name="agent_registry",
            builder=builder,
            agent_names=context.agent_names,
            tool_registry=tool_registry,
            agent_selector=agent_selector
            )
    
    def validate(self, container: FlotillaContainer, context: AgentContext):
        if not container.exists("agent_registry"):
            #raise an error
            raise FlotillaConfigurationError("AgentRegistry configuration failed validation")