from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"
