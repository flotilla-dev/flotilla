from pathlib import Path
from typing import Dict

from flotilla.config.sources.yaml_configuration_source import YamlConfigurationSource
from flotilla.config.secret_resolver import SecretResolver
from flotilla.config.config_loader import ConfigLoader
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.runtime.flotilla_runtime import FlotillaRuntime
from flotilla.tools.flotilla_tool import FlotillaTool


class SpySecretResolver(SecretResolver):
    def __init__(self, secrets: Dict[str, str]):
        self._secrets = secrets

    def resolve(self, secret_key):
        return self._secrets.get(secret_key, None)


class Tool1(FlotillaTool):
    def __init__(self, key: str):
        self.api_key = key

    def llm_description(self):
        return "stuff"

    def name(self):
        return "tool 1"

    def run(self):
        pass

    def execution_callable(self):
        return self.run


class InlineHandler:
    def __init__(self, label: str):
        self.label = label


def write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


async def test_configuration_e2e(tmp_path: Path, agent_factory, tool_factory, resume_service_valid, store, telemetry_service):

    def mock_agent_provider(**kwargs):
        return agent_factory(name="Mock Agent", **kwargs)

    def mock_tool2_provider():
        return tool_factory(name="list tool", description="stuff")

    def mock_resume_provider():
        return resume_service_valid

    def mock_telemtry_provider():
        return telemetry_service

    def mock_store_provider():
        return store

    def tool_1_provider(key: str):
        return Tool1(key=key)

    def mock_router_provider(handlers: Dict[str, object]):
        return {"handlers": handlers}

    write(
        path=tmp_path / "flotilla.yml",
        content="""
example:
    runtime:
        # reflection provider
        $class: flotilla.runtime.flotilla_runtime.FlotillaRuntime
        $name: runtime
        orchestration:
            # reference to $name value
            $ref: orchestration_strategy
        store:
            $ref: thread_store
        phase_context_service:
            $ref: phase_context
        execution_timeout_policy:
            $class: flotilla.timeout.default_execution_timeout_policy.DefaultExecutionTimeoutPolicy
            # constructor arg
            timeout_ms: 1000
        resume_service:
            # custom provider
            $provider: mock_resume_provider
        suspend_service:
            # reference to default name
            $ref: example.suspend_service
        telemetry_service:
            $ref: example.telemetry

    strategy:
        $class: flotilla.runtime.support.single_agent_orchestration.SingleAgentOrchestration
        $name: orchestration_strategy
        agent:
            $ref: agent
        telemetry: 
            $ref: example.telemetry

    store:
        $provider: fake_store_provider
        $name: thread_store

    phase_context:
        $class: flotilla.runtime.phase_context_service.DefaultPhaseContextService
        $name: phase_context

    suspend_service:
        # uses class exposed in __init__.py
        $class: flotilla.suspend.NoOpSuspendService

    telemetry:
        $provider: mock_telemetry_provider

# demo component as top level for reference
agent:
    $provider: mock_agent_provider
    tools:
        $list:
            - $ref: tool_factory
              $params:
                key:
                    $secret: secret_key
            - $provider: mock_tool_2_provider
tools:
    tool_factory:
        $factory: tool_1_provider
        $name: tool_factory

router:
    $provider: mock_router_provider
    handlers:
        $map:
            factory_tool:
                $ref: tool_factory
                $params:
                    key: map-tool
            inline_handler:
                $class: container.test_configuration_e2e.InlineHandler
                label: inline
""",
    )

    # create configuration source and secret resolver
    config_source = YamlConfigurationSource(path=tmp_path / "flotilla.yml")
    secret_resolver = SpySecretResolver(secrets={"secret_key": "testing"})

    # create config loader
    config_loader = ConfigLoader(sources=[config_source], secrets=[secret_resolver])
    settings = await config_loader.load()

    # create the container
    container = FlotillaContainer(settings=settings)
    # Register providers
    container.register_provider("mock_resume_provider", mock_resume_provider)
    container.register_provider("fake_store_provider", mock_store_provider)
    container.register_provider("mock_telemetry_provider", mock_telemtry_provider)
    container.register_provider("mock_agent_provider", mock_agent_provider)
    container.register_provider("mock_tool_2_provider", mock_tool2_provider)
    container.register_provider("tool_1_provider", tool_1_provider)
    container.register_provider("mock_router_provider", mock_router_provider)

    # start building the container
    await container.build()

    # ---------------------------
    # Check components were built and registered on the container
    # assert $provider, $class and $name
    # ---------------------------

    assert container.exists("runtime")
    assert container.exists("example.runtime.execution_timeout_policy")
    assert container.exists("example.runtime.resume_service")
    assert container.exists("orchestration_strategy")
    assert container.exists("thread_store")
    assert container.exists("phase_context")
    assert container.exists("example.suspend_service")
    assert container.exists("example.telemetry")
    assert container.exists("agent")
    assert container.exists("tool_factory")
    assert container.exists("router")

    # ---------------------------
    # Assert $ref
    # ---------------------------
    runtime: FlotillaRuntime = await container.get("runtime")

    assert runtime
    assert runtime._orchestration
    # confirm that orchestration on runtime is the same as the container
    assert runtime._orchestration is await container.get("orchestration_strategy")
    assert runtime._store
    assert runtime._phase_context_service
    assert runtime._resume_service
    assert runtime._suspend_service
    assert runtime._telemetry_service
    assert runtime._timeout_policy
    # assert embedded componet is attached to runtime and is the same as on the container
    assert runtime._timeout_policy is await container.get("example.runtime.execution_timeout_policy")

    # ---------------------------
    # Assert $list
    # ---------------------------

    agent = await container.get("agent")
    assert agent
    assert agent.extra_kwargs["tools"]
    assert len(agent.extra_kwargs["tools"]) == 2
    assert isinstance(agent.extra_kwargs["tools"][0], FlotillaTool)

    # ---------------------------
    # Assert $factory, $params and $secret
    # ---------------------------

    tool_from_agent = agent.extra_kwargs["tools"][0]
    assert isinstance(tool_from_agent, Tool1)
    assert tool_from_agent.api_key == "testing"

    tool_from_factory = await container.get("tool_factory", key="manual")
    assert isinstance(tool_from_factory, Tool1)
    assert tool_from_factory.api_key == "manual"
    assert tool_from_factory is not tool_from_agent

    # ---------------------------
    # Assert $map
    # ---------------------------

    router = await container.get("router")
    handlers = router["handlers"]

    assert isinstance(handlers["factory_tool"], Tool1)
    assert handlers["factory_tool"].api_key == "map-tool"
    assert handlers["factory_tool"] is not tool_from_agent
    assert handlers["factory_tool"] is not tool_from_factory

    assert isinstance(handlers["inline_handler"], InlineHandler)
    assert handlers["inline_handler"].label == "inline"
