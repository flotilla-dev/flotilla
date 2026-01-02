from __future__ import annotations
from typing import Protocol, TYPE_CHECKING, Generic, TypeVar, List

if TYPE_CHECKING:
    from flotilla.container.flotilla_container import FlotillaContainer

class WiringContributor(Protocol):
    name: str
    priority: int

    def contribute(self, container: FlotillaContainer) -> None:
        ...

    def validate(self, container: FlotillaContainer) -> None:
        ...


ContextT = TypeVar("ContextT")


class GroupedContributor(Protocol[ContextT]):
    def contribute(
        self,
        container: FlotillaContainer,
        context: ContextT,
    ) -> None:
        ...

    def validate(
        self,
        container: FlotillaContainer,
        context: ContextT,
    ) -> None:
        ...

        
class ContributorGroup(Generic[ContextT]):
    name: str
    priority: int

    def __init__(self):
        self._context: ContextT = self.create_context()
        self._contributors = self.create_contributors()

    def create_context(self) -> ContextT:
        raise NotImplementedError

    def create_contributors(self) -> list[GroupedContributor[ContextT]]:
        raise NotImplementedError

    def contribute(self, container: FlotillaContainer) -> None:
        for contributor in self._contributors:
            contributor.contribute(container, self._context)

    def validate(self, container: FlotillaContainer) -> None:
        for contributor in self._contributors:
            contributor.validate(container, self._context)

