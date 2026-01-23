from flotilla.container.base_contributors import WiringContributor
from flotilla.core.builders.orchestration_engine_buidler import orchestration_engine_builder
from flotilla.core.errors import FlotillaConfigurationError

class OrchestrationEngineContributor(WiringContributor):
    name = "Orchestratoin Engine Contributor"
    priority=1000

    def contribute(self, container):
        agent_registry = container.get("agent_registry")
        tool_registry = container.get("tool_registry")

        # hard code the builder function to ensure orchestration engine is created properly and to ensure it works even if developers forget to register the builder
        container.wire_infrastructure(name="orchestration_engine", builder=orchestration_engine_builder, agent_registry=agent_registry, tool_registry=tool_registry)
    
    def validate(self, container):
        if not container.exists("orchestration_engine"):
            raise FlotillaConfigurationError("OrchestrationEngine not registered on container")
        