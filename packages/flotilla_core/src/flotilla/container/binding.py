from abc import ABC, abstractmethod
from typing import Any


class Binding(ABC):
    @abstractmethod
    def resolve(self) -> Any: ...
