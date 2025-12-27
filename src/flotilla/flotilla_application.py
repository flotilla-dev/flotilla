from typing import Dict, List

from flotilla.builders.component_builder import ComponentBuilder
from flotilla.builders.builder_group import BuilderGroup
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.settings import FlotillaSettings
from flotilla.container.contributors.base_contributors import WiringContributor


class FlotillaApplication:
    def __init__(self, settings: FlotillaSettings):
        self.settings = settings
        self._contributors: List[WiringContributor] = []
        self._builders: Dict[str, ComponentBuilder] = {}
        self._container = None
        self._started = False

    # ----------------------------
    # Extension API (app-owned)
    # ----------------------------

    def register_builder(self, builder_name: str, builder: ComponentBuilder):
        self._builders[builder_name] = builder

    def register_builder_group(self, group:BuilderGroup):
        for name, builder in group.builders().items():
            self.register_builder(name, builder)

    def register_contributor(self, contributor: WiringContributor):
        self._contributors.append(contributor)

    # ----------------------------
    # Build lifecycle
    # ----------------------------

    def _build_container(self) -> FlotillaContainer:
        container = FlotillaContainer(self.settings)

        # Apply builders
        for name, builder in self._builders.items():
            container.register_builder(name, builder)

        # Apply contributors
        for contributor in self._contributors:
            container.register_contributor(contributor)

        return container.build()

    def start(self):
        self._container = self._build_container()
        self._started = True


    def shutdown(self):
        if not self._started:
            return

        # Optional: graceful teardown hooks later
        self._container = None
        self._started = False


    # ----------------------------
    # Accessors
    # ----------------------------
    
    @property
    def container(self) -> FlotillaContainer:
        if not self._started:
            raise RuntimeError("Application not started")
        return self._container

    @property
    def started(self) -> bool:
        return self._started