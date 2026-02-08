from typing import Protocol
from langchain.chat_models.base import BaseChatModel
from langgraph.types import Checkpointer
from flotilla.container.component_factory import ComponentFactory
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.agents.base_business_agent import BaseBusinessAgent

class AgentFactory(ComponentFactory, Protocol):
    """
    Builder protocol for constructing Business Agents.

    An AgentBuilder is responsible for instantiating a concrete
    ``BaseBusinessAgent`` using agent-specific configuration and
    framework-provided runtime dependencies.

    This protocol formalizes the contract between the Flotilla framework
    and application-defined agent builders.

    --------------------
    Responsibility Split
    --------------------
    The Flotilla framework owns and provides all *platform-level*
    dependencies required by an agent, including but not limited to:
      - the LLM instance used for inference
      - the Checkpointer used for state persistence and recovery

    Agent builders MUST NOT construct or configure these dependencies
    themselves. Instead, they receive fully constructed instances from
    the framework and are responsible only for:
      - selecting the concrete agent class
      - interpreting agent-specific configuration
      - resolving any domain-specific dependencies
      - returning a fully initialized agent instance

    --------------------
    Invocation Contract
    --------------------
    AgentBuilder instances are invoked by the framework during container
    build, after all required infrastructure components have been wired.

    The builder is always called with the following keyword arguments:

      - container:
          The active Flotilla dependency container. Builders may resolve
          additional domain-specific dependencies from this container if
          required.

      - config:
          The resolved configuration dictionary for this agent, sourced
          from the application configuration. The contents of this
          dictionary are agent-specific.

      - llm:
          A fully constructed LLM instance selected and configured by
          the framework according to application policy.

      - checkpointer:
          A Checkpointer instance used by the agent for execution state
          management.

    --------------------
    Return Value
    --------------------
    The builder MUST return an instance of ``BaseBusinessAgent`` that is
    fully constructed and ready for lifecycle management by the
    framework.

    Returning ``None`` or an incorrectly constructed agent is considered
    a configuration error and may result in container build failure.

    --------------------
    Design Notes
    --------------------
    This protocol intentionally extends ``ComponentBuilder`` rather than
    replacing it, allowing AgentBuilder implementations to participate
    in generic builder registration and tooling while providing stronger
    guarantees for agent construction.

    AgentBuilder implementations are expected to be lightweight and
    deterministic. Any cross-cutting concerns (LLM policy, retries,
    tracing, caching, environment selection) must be handled by the
    framework, not by the builder.
    """
    def __call__(self, *, container: FlotillaContainer, config: dict, llm: BaseChatModel, checkpointer: Checkpointer) -> BaseBusinessAgent:
        ...
