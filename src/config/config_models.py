"""
Configuration models for the orchestration system
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from config.settings import Settings
from langchain_core.tools import StructuredTool

class FeatureConfig(BaseModel):
    """
    Base config object that should be extended by any config object that wishes to have feature flags set on it
    """
    feature_flags: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Feature flag toggles active for this environment"
    )    

class LLMConfig(FeatureConfig):
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



class ToolRegistryConfig(FeatureConfig):
    """Configuration for Tool Registry"""
    tool_discovery: bool = Field(default=True, description="Controls if Tools should be automatically discovered")
    tool_packages:List[str] | None = Field(default=[], description="A list of packages to load tools from")
    tool_recursive: bool = Field(default=True, description="If the Tool Registry should load recusrively")
    settings: Settings = Field(..., description="The full settings for the application")

class AgentRegistryConfig(FeatureConfig):
    """Configuration for Agent Registry"""
    agent_discovery: bool = Field(default=True, description="Controls if Agents should automatcally be discovered")
    agent_packages:List[str] | None = Field(default=[], description="A list of packages to load agents from")
    agent_recursive: bool = Field(default=True, description="If the Agent Registry should load recurisvely")
    llm_config: LLMConfig | None = Field(default=None, description="The LLMConfig to use with the AgentRegistry")
    settings: Settings = Field(..., description="The full settings for the application")
    

class BusinessAgentConfg(FeatureConfig):
    """Configuration for a BusinesAgent"""
    llm_config: LLMConfig = Field(default=None, description="The LLMConfig for use in the BusinessAgent")
    tools: List[StructuredTool] | None = Field(default = [], description="List of Tools that be passed to the Agent")
    agent_configuration: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional agent configuration data"
    )


class ClientConfig(FeatureConfig):
    """Complete configuration for a single client"""
    client_id: str = Field(..., description="Unique client identifier")
    client_name: str = Field(..., description="Client name")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional client metadata"
    )


class OrchestrationConfig(FeatureConfig):
    """Master orchestration configuration"""
    client: ClientConfig = Field(..., description="Configuration for the current client")
    log_level: str = Field(default="INFO", description="Logging level")
    llm_config: LLMConfig = Field(..., description="Config for the LLM used by the Orchestration Agent"),
    tool_registry_config:ToolRegistryConfig = Field(..., description="Configuration for the Tool Registry"),
    agent_registry_config:AgentRegistryConfig = Field(..., description="Configuratoin for the Agent Registry")

class ToolConfig(FeatureConfig):
    """Configuration for a BaseTool class"""
    tool_configuration: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional tool configuration data"
    )   
