from flotilla.container.component_provider import ComponentProvider


class ProviderGroup:
    def builders(self) -> dict[str, ComponentProvider]:
        raise NotImplementedError
