"""
Configuration models for the orchestration system
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """Configugration for LLM"""
    #endpoint: str = Field(..., description="LLM endpoint URL")
    api_key: str = Field(..., description="LLM API key")
    model_name: str = Field(default="gpt-4o-mini", description="The name of the model version to use")
    temperature: float = Field(default=0.1, description="Temperature for LLM responses")
    max_tokens: Optional[int] = Field(default=2000, description="Maximum tokens in response")


class ToolRegistryConfig(BaseModel):
    """Configuration for Tool Registry"""
    tool_discovery: bool = Field(default=True, description="COntrols if Tools should be automatically discovered")
    tool_packages:List[str] = Field(..., description="A list of packages to load tools from")
    tool_recursive: bool = Field(default=True, description="If the Tool Registry should load recusrively")

class AgentRegistryConfig(BaseModel):
    """Configuration for Agent Registry"""
    agent_discovery: bool = Field(default=True, description="Controls if Agents should automatcally be discovered")
    agent_packages:List[str] = Field(..., description="A list of packages to load agents from")
    agent_recursive: bool = Field(default=True, description="If the Agent Registry should load recurisvely")
    llm_config:LLMConfig = Field(..., description="The LLMConfig to use with the AgentRegistry")

'''
class AzureOpenAIConfig(BaseModel):
    """Configuration for Azure OpenAI service"""
    endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    api_key: str = Field(..., description="Azure OpenAI API key")
    api_version: str = Field(default="2024-02-15-preview", description="API version")
    deployment_name: str = Field(default="gpt-4", description="GPT-4 deployment name")
    temperature: float = Field(default=0.7, description="Temperature for LLM responses")
    max_tokens: Optional[int] = Field(default=2000, description="Maximum tokens in response")

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
    llm_config: LLMConfig = Field(..., description="Config for the LLM used by the Client")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional client metadata"
    )


class OrchestrationConfig(BaseModel):
    """Master orchestration configuration"""
    client: ClientConfig = Field(..., description="Configuration for the current client")
    log_level: str = Field(default="INFO", description="Logging level")
    enable_tracing: bool = Field(default=True, description="Enable request tracing")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    llm_config: LLMConfig = Field(..., description="Config for the LLM used by the Orchestration Agent")