from __future__ import annotations

from typing import Protocol, Any, Awaitable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from flotilla.container.flotilla_container import FlotillaContainer


class ComponentProvider(Protocol):
    """
    A callable responsible for constructing a framework component
    from configuration and container context.
    """

    def __call__(
        self,
        *,
        container: FlotillaContainer,
        config: Optional[dict],
        **kwargs: Any,
    ) -> Any | Awaitable[Any]: ...
