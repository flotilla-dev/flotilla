from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.container.contributors.tools.context import ToolsContext
from flotilla.flotilla_configuration_error import FlotillaConfigurationError


class ToolRegistryContributor:
    def contribute(self, container: FlotillaContainer, context: ToolsContext) -> None:
        builder = container.get_builder("tool_registry")
        if not builder:
            raise FlotillaConfigurationError("ToolRegistry builder not registered")

        container.wire_infrastructure(
            name="tool_registry",
            builder=builder,
            tool_provider_names=context.tool_provider_names
)
        

    def validate(self, container:FlotillaContainer, context:ToolsContext):
        if not context.tool_provider_names:
            return

        if not hasattr(container.di, "tool_registry"):
            raise RuntimeError("ToolRegistry not wired")
