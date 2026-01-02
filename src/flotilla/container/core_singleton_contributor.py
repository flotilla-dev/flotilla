from flotilla.container.flotilla_container import FlotillaContainer, WiringContributor
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)


class CoreSingletonsContributor(WiringContributor):
    name = "core-singletons"
    priority = 100

    def contribute(self, container: FlotillaContainer):
        cfg = container.di.config.core if hasattr(container.di.config, "flotilla") else None
        if not cfg:
            logger.warn("No configuration exists for 'flotilla' section")
            return

        container.wire_from_config(
            section="core",
            name="agent_selector",
            config_path="agent_selector",
        )

        container.wire_from_config(
            section="core",
            name="checkpointer",
            config_path="checkpointer",
        )

    def validate(self, container: FlotillaContainer):
        # Optional, but powerful
        if not hasattr(container.di, "agent_selector"):
            raise RuntimeError("agent_selector not wired")
