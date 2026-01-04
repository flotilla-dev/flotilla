# tests/test_weather_agent_integration.py
import pytest
from example_app.src.app_agents.weather_agent import WeatherAgent

import uuid
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)

'''
@pytest.mark.integration
def test_weather_agent_real_llm():
    #set_debug(True)
    # Arrange
    settings = ConfigLoader.load("UAT", "example_app/src/config")
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
    thread_id = uuid.uuid4()
    context = {"configurable": {"thread_id": thread_id}}
    query = "What is current weather in Denver??"
    result = agent.execute(query, context=context)
    #result = agent.execute(query)

    # Assert structure
    assert result is not None
    assert isinstance(result, BusinessAgentResponse)
    assert result.status == ResponseStatus.SUCCESS
    assert "Denver" in result.message
    #logger.info(f"Response from LLM {result}")
'''
