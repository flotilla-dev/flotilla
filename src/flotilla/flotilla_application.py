from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.settings import FlotillaSettings
from flotilla.container.builders.default_builders import (
    keyword_agent_selector_builder,
    memory_checkpointer_builder,
)


class FlotillaApplication:
    def __init__(self, settings: FlotillaSettings):
        self.settings = settings

    def register_builders(self, container: FlotillaContainer):
        """
        Register default Flotilla framework builders.
        """
        container.register_builder(
            "agent_selector.keyword",
            keyword_agent_selector_builder,
        )
        container.register_builder(
            "checkpointer.memory",
            memory_checkpointer_builder,
        )

    def build_container(self) -> FlotillaContainer:
        container = FlotillaContainer(self.settings)
        self.register_builders(container)
        return container.build()

    def start(self):
        pass

    def shutdown(self):
        pass
