from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


class ToolConfig(BaseModel):
    """Configuration for a BaseTool class"""
    tool_discovery: bool = Field(default=True, description="Controls if the ToolFactory instance that receives this config will run autodiscovery of embeeded tools")
    tool_configuration: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional tool configuration data"
    ) 