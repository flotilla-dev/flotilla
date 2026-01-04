
from flotilla.container.base_contributors import WiringContributor
from flotilla.container.flotilla_container import FlotillaContainer

class CheckpointContributor(WiringContributor):
    name = "Checkpoint Contributor"
    priority = 2

    def contribute(self, container:FlotillaContainer):
        container.wire_from_config(section="flotilla", name="checkpointer", config_path="checkpointer")
    
    def validate(self, container):
        pass