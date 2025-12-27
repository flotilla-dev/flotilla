from dataclasses import dataclass, field
from typing import List


@dataclass
class ToolsContext:
    tool_provider_names: List[str] = field(default_factory=list)
