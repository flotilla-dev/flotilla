from typing import Dict, Callable, List

from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.settings import FlotillaSettings
from flotilla.container.builders.default_builders import (
    keyword_agent_selector_builder,
    memory_checkpointer_builder,
)
from flotilla.container.contributors.tools.group import ToolsContributorGroup
from flotilla.container.contributors.base_contributors import WiringContributor


class FlotillaApplication:
    def __init__(self, settings: FlotillaSettings):
        self.settings = settings
        self._contributors: List[WiringContributor] = []
        self._builders: Dict[str, Callable] = {}
        self._container = None
        self._started = False

        # Register framework defaults
        #self._register_default_builders()
        #self._register_default_contributors()

    # ----------------------------
    # Defaults (framework-owned)
    # ----------------------------

    def _register_default_builders(self):
        self._builders["agent_selector.keyword"] = keyword_agent_selector_builder
        self._builders["checkpointer.memory"] = memory_checkpointer_builder

    def _register_default_contributors(self):
        self._contributors.append(ToolsContributorGroup())

    # ----------------------------
    # Extension API (app-owned)
    # ----------------------------

    def register_builder(self, builder_name: str, builder: Callable):
        self._builders[builder_name] = builder

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
        if not self._started or not self._container:
            raise RuntimeError("Application not started")
        return self._container
    
    @property
    def started(self) -> bool:
        return self._started