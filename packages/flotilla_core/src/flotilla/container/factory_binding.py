from .binding import Binding


class FactoryBinding(Binding):
    def __init__(self, factory, **kwargs):
        self._factory = factory
        self._kwargs = kwargs

    def resolve(self):
        return self._factory(**self._kwargs)
