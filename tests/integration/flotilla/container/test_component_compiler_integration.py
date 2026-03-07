from typing import List, Dict, Any

from langchain_core.tools.structured import StructuredTool
from langchain.chat_models import BaseChatModel
from langgraph.types import Checkpointer
from langgraph.checkpoint.memory import InMemorySaver

from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.flotilla_settings import FlotillaSettings
from flotilla.runtime.flotilla_runtime import FlotillaRuntime
from flotilla.tools.flotilla_tool import FlotillaTool


config = {
    "llm": {
        "mock": {
            "factory": "llm.mock",
            "ref_name": "llm",
            "model": "gpt-4o-mini",
            "api_key": "abc123",
            "temperature": 0.5,
        }
    },
    "tools": {
        "weather": {
            "factory": "tools.weather",
            "api_key": "weather-key",
            "base_url": "https://api.weather.com",
        },
        "audit": {
            "factory": "tools.audit",
            "level": "debug",
        },
    },
    "agents": {
        "composite": {
            "factory": "agents.composite",
            "llm": {"$ref": "llm"},
            "tools": {
                "$list": [
                    {"$ref": "tools.weather"},
                    {"$ref": "tools.audit"},
                    {"factory": "tools.inline", "name": "inline_tool"},
                ]
            },
            "metadata": {
                "$map": {
                    "owner": "Geoff",
                    "selector": {
                        "factory": "agent_selector.keyword",
                        "min_confidence": 0.5,
                    },
                }
            },
            "checkpointer": {"factory": "checkpointer.memory"},
        }
    },
    "runtime": {
        "main": {"factory": "runtime.mock", "agent": {"$ref": "agents.composite"}}
    },
}


def test_full_graph_integration(
    tool_factory,
    agent_factory,
    mock_flotilla_runtime_factory,
    llm_factory,
):

    # -------------------------------
    # define factory functions
    # -------------------------------
    def mock_llm_factory(model: str, api_key: str, temperature: float) -> BaseChatModel:
        return llm_factory(model=model, api_key=api_key, temperature=temperature)

    def composite_agent_factory(
        llm: BaseChatModel,
        tools: List[StructuredTool],
        metadata: Dict,
        checkpointer: Checkpointer,
    ) -> Any:
        pass

    def weather_tool_factory(api_key: str, base_url: str) -> FlotillaTool:
        return tool_factory(
            name="Weather Tool",
            description="Call to get weather data",
            api_key=api_key,
            base_url=base_url,
        )

    def audit_tool_factory(level: str) -> FlotillaTool:
        return tool_factory(
            name="Audit Tool", description="Mock audit tool", level=level
        )

    def inline_tool_factory(name: str) -> FlotillaTool:
        return tool_factory(
            name=name,
            description="description",
        )

    def mock_runtime_factory(agent: Any) -> FlotillaRuntime:
        return mock_flotilla_runtime_factory(agent=agent)

    def memory_checkpointer_factory() -> Checkpointer:
        return InMemorySaver()

    # -------------------------------
    # Setup the container and build
    # -------------------------------
    """
    settings = FlotillaSettings(config)
    container = FlotillaContainer(settings=settings)
    # ---- Add Factories ------
    container.register_factory("llm.mock", mock_llm_factory)
    container.register_factory("tools.weather", weather_tool_factory)
    container.register_factory("tools.audit", audit_tool_factory)
    container.register_factory("agents.composite", composite_agent_factory)
    container.register_factory("runtime.mock", mock_runtime_factory)
    container.register_factory("tools.inline", inline_tool_factory)
    container.register_factory("checkpointer.memory", memory_checkpointer_factory)

    container.build()

    # -------------------------------
    # Check top line components
    # -------------------------------
    assert container.exists("runtime.main")
    assert container.exists("llm")
    assert not container.exists(
        "llm.mock"
    )  # validates that ref_name is used instead of path
    assert container.exists("tools.weather")
    assert container.exists("tools.audit")
    assert container.exists("agents.composite")

    # -------------------------------
    # Check embedded components are registered
    # -------------------------------
    assert container.exists("agents.composite.tools.$list[2]")
    assert container.exists("agents.composite.metadata.selector")

    # -------------------------------
    # Check refs
    # -------------------------------

    llm = container.get("llm")
    agent = container.get("agents.composite")
    assert agent._llm is llm

    runtime = container.get("runtime.main")
    assert runtime.extra_kwargs["agent"] is agent

    # -------------------------------
    # Check inline factory
    # -------------------------------
    assert agent._checkpointer
    assert isinstance(agent._checkpointer, InMemorySaver)

    # -------------------------------
    # Check list and map
    # -------------------------------

    assert agent.tools
    weather_tool = container.get("tools.weather")
    assert weather_tool in agent.tools
    assert container.get("tools.audit") in agent.tools
    assert len(agent.tools) == 3

    assert agent.extra_kwargs["metadata"]
    assert agent.extra_kwargs["metadata"]["owner"] == "Geoff"

    selector = agent.extra_kwargs["metadata"]["selector"]
    assert selector
    assert selector.min_confidence == 0.5
"""
