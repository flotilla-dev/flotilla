from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.container.contributors.tools.context import ToolsContext


class ToolProvidersContributor:
    def contribute(self, container: FlotillaContainer, context: ToolsContext) -> None:
        tools_cfg_opt = getattr(container.di.config, "tools", None)
        if not tools_cfg_opt:
            return

        tools_cfg = tools_cfg_opt()
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
