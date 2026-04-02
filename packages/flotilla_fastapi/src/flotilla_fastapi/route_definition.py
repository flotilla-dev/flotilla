from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class RouteDefinition:
    http_method: str
    path: str
    kwargs: Dict[str, Any]
    method_name: str
