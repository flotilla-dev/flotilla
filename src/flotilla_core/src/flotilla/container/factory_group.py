from flotilla.container.component_factory import ComponentFactory

class FactoryGroup:
    def builders(self) -> dict[str, ComponentFactory]:
        raise NotImplementedError
