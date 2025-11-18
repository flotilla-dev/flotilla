# tests/test_weather_agent_integration.py
import os
import pytest
from agents.business_logic.weather_agent import WeatherAgent
from config.settings import Settings
from config.config_loader import ConfigLoader
from config.config_factory import ConfigFactory
from tools.tool_registry import ToolRegistry
from agents.business_agent_response import BusinessAgentResponse

@pytest.mark.integration
def test_weather_agent_real_llm():
    # Arrange
    settings = ConfigLoader.load("UAT")
    agent = WeatherAgent()

    tool_registry_config = ConfigFactory.create_tool_registry_config(settings=settings)
    tool_registry = ToolRegistry(tool_registry_config)

    # Inject LLM config (your BaseBusinessAgent should support this)
    config = ConfigFactory.create_business_agent_config(agent.agent_name, settings)
    agent.configure(config)
    tools = tool_registry.get_tools(agent.filter_tools)
    agent.attach_tools(tools)
    agent.startup()

    # Act
    query = "What's the forecast in Chicago tomorrow?"
    result = agent.execute(query)

    # Assert structure
    assert result is not None
    assert isinstance(result, BusinessAgentResponse)
    print(f"Response from LLM {result}")

