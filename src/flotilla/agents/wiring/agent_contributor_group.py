from flotilla.agents.wiring.agent_context import AgentContext
from flotilla.agents.wiring.agent_contributor import AgentContributor
from flotilla.agents.wiring.agent_registry_contributor import AgentRegistryContributor
from flotilla.container.base_contributors import ContributorGroup

class AgentContributorGroup(ContributorGroup[AgentContext]):
    name = "agents"
    priority = 50

    def create_context(self) -> AgentContext:
        return AgentContext()
    
    def create_contributors(self):
        return [
            AgentContributor(),
            AgentRegistryContributor()
        ]