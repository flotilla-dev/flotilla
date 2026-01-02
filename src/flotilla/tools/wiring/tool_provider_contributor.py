from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.tools.wiring.tool_context import ToolsContext


class ToolProvidersContributor:
    def contribute(self, container: FlotillaContainer, context: ToolsContext) -> None:
        tools_cfg = container.config_dict.get("tools")
        if not tools_cfg:
            return

        for name in tools_cfg.keys():
            # Delegate all config + builder resolution to the container
            container.wire_from_config(
                section="tools",
                name=name,
                config_path=name,
            )

            context.tool_provider_names.append(name)

    def validate(self, container, context):
        pass
