from flotilla.container.component_builder import ComponentBuilder

class BuilderGroup:
    def builders(self) -> dict[str, ComponentBuilder]:
        raise NotImplementedError
