from flotilla.container.flotilla_container import FlotillaContainer, WiringContributor

class CoreSingletonsContributor(WiringContributor):
    name = "core-singletons"
    priority = 100

    def contribute(self, container: FlotillaContainer):
        cfg = container.di.config.core if hasattr(container.di.config, "core") else None
        if not cfg:
            return

        container._register_section_singleton(
            section="core",
            name="agent_selector",
            config_path="agent_selector",
        )

        container._register_section_singleton(
            section="core",
            name="checkpointer",
            config_path="checkpointer",
        )

    def validate(self, container: FlotillaContainer):
        # Optional, but powerful
        if not hasattr(container.di, "agent_selector"):
            raise RuntimeError("agent_selector not wired")
