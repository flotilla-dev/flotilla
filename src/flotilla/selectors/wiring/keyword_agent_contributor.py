from flotilla.container.base_contributors import WiringContributor
from flotilla.container.flotilla_container import FlotillaContainer

class KeywordAgentSelectorContributor(WiringContributor):

    name = "Keyword AgentSelector Contributor"
    priority = 1

    def contribute(self, container: FlotillaContainer):
        container.wire_from_config(section="flotilla", name="agent_selector", config_path="agent_selector")
    
    def validate(self, container:FlotillaContainer):
        pass
