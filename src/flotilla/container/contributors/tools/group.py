from flotilla.container.contributors.base_contributors import ContributorGroup
from flotilla.container.contributors.tools.context import ToolsContext
from flotilla.container.contributors.tools.providers import ToolProvidersContributor
from flotilla.container.contributors.tools.registry import ToolRegistryContributor


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

