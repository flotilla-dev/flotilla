from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.container.contributors.tools.context import ToolsContext


class ToolRegistryContributor:
    def contribute(self, container: FlotillaContainer, context: ToolsContext) -> None:
        if not context.tool_names:
            return

        container.register_section_singleton(
            section="core",
            name="tool_registry",
            config_path="tool_registry",
            tool_providers=context.tool_names,
        )

    def validate(self, container, context):
        if context.tool_names and not hasattr(container.di, "tool_registry"):
            raise RuntimeError("ToolRegistry not wired")
