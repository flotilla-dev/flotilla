from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.container.contributors.tools.context import ToolsContext


class ToolProvidersContributor:
    def contribute(self, container: FlotillaContainer, context: ToolsContext) -> None:
        tools_cfg = getattr(container.di.config, "tools", None)
        if not tools_cfg:
            return

        for name, cfg in tools_cfg().items():
            builder_name = cfg.get("type")
            builder = container._builders.get(builder_name)
            if not builder:
                raise ValueError(
                    f"No builder registered for tool type '{builder_name}'"
                )

            container.register_component_provider(
                section="tools",
                name=name,
                builder=builder,
            )
            context.tool_names.append(name)

    def validate(self, container, context):
        pass
