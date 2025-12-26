from __future__ import annotations

from dependency_injector import containers, providers
from typing import Callable, List, Protocol

from flotilla.config.settings import FlotillaSettings
from flotilla.utils.logger import get_logger



logger = get_logger(__name__)

class WiringContributor(Protocol):
    name: str
    priority: int

    def contribute(self, container: FlotillaContainer) -> None:
        ...

    def validate(self, container: FlotillaContainer) -> None:
        ...


class FlotillaContainer:
    """
    DI container for Flotilla.

    Responsibilities:
    - Own Dependency Injector container
    - Expose configuration to providers
    - Register builders
    - Execute wiring logic (for now, via build())
    """

    def __init__(self, settings: FlotillaSettings):
        self.settings = settings

        self.di = containers.DeclarativeContainer()
        self.di.config = providers.Configuration()

        # Mount immutable config snapshot into DI
        self.di.config.from_dict(
            settings.model_dump(exclude_none=True)
        )

        self._builders: dict[str, Callable] = {}

    # ----------------------------
    # Registration Methods
    # ----------------------------

    def register_builder(self, builder_name: str, builder: Callable):
        """
        Register a builder function that can be referenced by name in config.
        """
        logger.info(f"Register builder '{builder_name}'")
        self._builders[builder_name] = builder

    def register_contributor(self, contributor: WiringContributor):
        self._contributors.append(contributor)

    # ----------------------------
    # Internal Wiring Helpers
    # ----------------------------

    def _register_component_provider(
        self,
        *,
        section: str,
        name: str,
        builder: Callable,
    ):
        config_option = getattr(self.di.config, section)[name]

        setattr(
            self.di,
            name,
            providers.Factory(
                builder,
                name=name,
                config=config_option,
                container=self.di,
            ),
        )

    def _register_singleton(self, name: str, builder: Callable, **deps):
        setattr(
            self.di,
            name,
            providers.Singleton(builder, **deps),
        )

    def _register_section_singleton(
        self,
        *,
        section: str,
        name: str,
        config_path: str,
        **kwargs,
    ):
        logger.info(
            f"Register singleton '{name}' from config section '{section}'"
        )

        section_cfg = getattr(self.di.config, section, None)
        if not section_cfg:
            return

        cfg = getattr(section_cfg, config_path, None)
        if not cfg:
            return

        data = cfg()
        if not data:
            return

        builder_name = data.get("builder")
        if not builder_name:
            raise ValueError(
                f"{section}.{config_path}.builder is required"
            )

        builder = self._builders.get(builder_name)
        if not builder:
            raise ValueError(
                f"No builder registered for '{builder_name}'"
            )

        self._register_singleton(
            name,
            builder,
            container=self.di,
            config=data,
            **kwargs,
        )

    # ----------------------------
    # Build (temporary, will shrink)
    # ----------------------------

    def build(self):
        """
        Build the DI container.

        NOTE:
        This method will be decomposed into contributors next.
        """
        logger.info("Building Flotilla DI container")

        provider_refs: List[str] = []

        # Tools & agents (existing behavior preserved)
        for section in ("tools", "agents"):
            section_cfg = getattr(self.di.config, section, None)
            if not section_cfg:
                continue

            section_data = section_cfg()
            if not section_data:
                continue

            for name, cfg in section_data.items():
                component_type = cfg.get("type")
                if component_type not in self._builders:
                    raise ValueError(
                        f"No builder registered for '{component_type}'"
                    )

                self._register_component_provider(
                    section=section,
                    name=name,
                    builder=self._builders[component_type],
                )

                if section == "tools":
                    provider_refs.append(name)

        # Core components (unchanged)
        self._register_section_singleton(
            section="core",
            name="tool_registry",
            config_path="tool_registry",
            tool_providers=provider_refs,
        )

        self._register_section_singleton(
            section="core",
            name="agent_selector",
            config_path="agent_selector",
        )

        self._register_section_singleton(
            section="core",
            name="checkpointer",
            config_path="checkpointer",
        )

        logger.info("✓ Flotilla container build complete")

        return self



