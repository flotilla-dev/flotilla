"""
Configuration models for the orchestration system
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from config.settings import Settings
from langchain_core.tools import StructuredTool



class LLMConfig(BaseModel):
    """Configugration for LLM"""
    api_key: str = Field(..., description="LLM API key")
    temperature: float = Field(default=0.1, description="Temperature for LLM responses")
    max_tokens: Optional[int] = Field(default=2000, description="Maximum tokens in response")


class OpenAIConfig(LLMConfig):
    """Configuration for standard OpenAI service"""
    model_name: str = Field(default="gpt-4o-mini", description="The name of the model version to use")


class AzureOpenAIConfig(LLMConfig):
    """Configuration for Azure OpenAI service"""
    endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    api_version: str = Field(default="2024-02-15-preview", description="API version")
    deployment_name: str = Field(default="gpt-4", description="GPT-4 deployment name")



class ToolRegistryConfig(BaseModel):
    """Configuration for Tool Registry"""
    tool_discovery: bool = Field(default=True, description="Controls if Tools should be automatically discovered")
    tool_packages:List[str] | None = Field(default=[], description="A list of packages to load tools from")
    tool_recursive: bool = Field(default=True, description="If the Tool Registry should load recusrively")

class AgentRegistryConfig(BaseModel):
    """Configuration for Agent Registry"""
    agent_discovery: bool = Field(default=True, description="Controls if Agents should automatcally be discovered")
    agent_packages:List[str] | None = Field(default=[], description="A list of packages to load agents from")
    agent_recursive: bool = Field(default=True, description="If the Agent Registry should load recurisvely")
    llm_config: LLMConfig | None = Field(default=None, description="The LLMConfig to use with the AgentRegistry")
    settings: Settings = Field(..., description="The full settings for the application")
    

class BusinessAgentConfg(BaseModel):
    """Configuration for a BusinesAgent"""
    llm_config: LLMConfig = Field(default=None, description="The LLMConfig for use in the BusinessAgent")
    tools: List[StructuredTool] | None = Field(default = [], description="List of Tools that be passed to the Agent")
    agent_configuration: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional agent configuration data"
    )



'''
class FabricWorkspaceConfig(BaseModel):
    """Configuration for Microsoft Fabric workspace"""
    workspace_id: str = Field(..., description="Fabric workspace ID")
    lakehouse_id: str = Field(..., description="Lakehouse ID")
    lakehouse_name: str = Field(..., description="Lakehouse name")
    endpoint: str = Field(..., description="Fabric REST API endpoint")
    tenant_id: str = Field(..., description="Azure tenant ID")


class BlockMCPConfig(BaseModel):
    """Configuration for Block MCP server"""
    server_command: str = Field(
        default="npx",
        description="Command to run MCP server"
    )
    server_args: List[str] = Field(
        default=["-y", "@modelcontextprotocol/server-square"],
        description="Arguments for MCP server"
    )
    access_token: str = Field(..., description="Block/Square API access token")
    environment: str = Field(
        default="production",
        description="Block environment (sandbox or production)"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")
'''

class ClientConfig(BaseModel):
    """Complete configuration for a single client"""
    client_id: str = Field(..., description="Unique client identifier")
    client_name: str = Field(..., description="Client name")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional client metadata"
    )


class OrchestrationConfig(BaseModel):
    """Master orchestration configuration"""
    client: ClientConfig = Field(..., description="Configuration for the current client")
    log_level: str = Field(default="INFO", description="Logging level")
    llm_config: LLMConfig = Field(..., description="Config for the LLM used by the Orchestration Agent"),
    tool_registry_config:ToolRegistryConfig = Field(..., description="Configuration for the Tool Registry"),
    agent_registry_config:AgentRegistryConfig = Field(..., description="Configuratoin for the Agent Registry")
