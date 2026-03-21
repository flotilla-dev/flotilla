from .binding import Binding


class SingletonBinding(Binding):
    def __init__(self, instance):
        self._instance = instance

    def resolve(self):
        return self._instance
