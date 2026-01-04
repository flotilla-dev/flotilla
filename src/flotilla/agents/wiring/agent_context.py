from dataclasses import dataclass, field
from typing import List


@dataclass
class AgentContext:
    agent_names: List[str] = field(default_factory=list)