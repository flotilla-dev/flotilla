from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.tools.wiring.tool_context import ToolsContext
from flotilla.core.errors import FlotillaConfigurationError
from flotilla.tools.builders.tool_registry_builder import tool_registry_builder


class ToolRegistryContributor:
    def contribute(self, container: FlotillaContainer, context: ToolsContext) -> None:
        container.wire_infrastructure(
            name="tool_registry",
            builder=tool_registry_builder,
            container=container,
            tool_provider_names=context.tool_provider_names
        )

        

    def validate(self, container:FlotillaContainer, context:ToolsContext):
        if not context.tool_provider_names:
            return
        
        if not container.exists("tool_registry"):
            raise FlotillaConfigurationError("ToolRegistry not wired on container")
