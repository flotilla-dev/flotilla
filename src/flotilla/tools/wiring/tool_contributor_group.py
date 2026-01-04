from flotilla.container.base_contributors import ContributorGroup
from flotilla.tools.wiring.tool_context import ToolsContext
from flotilla.tools.wiring.tool_provider_contributor import ToolProvidersContributor
from flotilla.tools.wiring.tool_registry_contributor import ToolRegistryContributor


class ToolsContributorGroup(ContributorGroup[ToolsContext]):
    name = "tools"
    priority = 10

    def create_context(self) -> ToolsContext:
        return ToolsContext()

    def create_contributors(self):
        return [
            ToolProvidersContributor(),
            ToolRegistryContributor(),
        ]

