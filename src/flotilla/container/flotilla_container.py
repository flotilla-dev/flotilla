from __future__ import annotations

from dependency_injector import containers, providers
from typing import Callable, List

from flotilla.config.settings import FlotillaSettings
from flotilla.container.contributors.base_contributors import WiringContributor
from flotilla.utils.logger import get_logger



logger = get_logger(__name__)



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
        self.di.config.from_dict(
            settings.model_dump(exclude_none=True)
        )

        self._builders: dict[str, Callable] = {}
        self._contributors: List[WiringContributor] = []

    # ----------------------------
    # Public API
    # ----------------------------

    def register_builder(self, builder_name: str, builder: Callable):
        """
        Register a builder function that can be referenced by name in config.
        """
        logger.info(f"Register builder '{builder_name}'")
        self._builders[builder_name] = builder

    def register_contributor(self, contributor: WiringContributor):
        self._contributors.append(contributor)


    def register_section_singleton(self, *, section: str, name: str, config_path: str, **kwargs):
        logger.info(f"Register singleton '{name}' from config section '{section}'")

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

        self.register_singleton(
            name,
            builder,
            container=self.di,
            config=data,
            **kwargs,
        )

    def register_component_provider(
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

    def register_singleton(self, name: str, builder: Callable, **deps):
        setattr(
            self.di,
            name,
            providers.Singleton(builder, **deps),
        )


    def build(self) -> FlotillaContainer:
        logger.info("Building Flotilla container")

        for contributor in sorted(
            self._contributors, key=lambda c: c.priority
        ):
            contributor.contribute(self)

        for contributor in self._contributors:
            contributor.validate(self)

        logger.info("✓ Flotilla container build complete")
        return self



