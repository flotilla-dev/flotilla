from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.core.errors import FlotillaConfigurationError


class LLMFactory:

    @staticmethod
    def create(container: FlotillaContainer, llm_config: dict):
        """
        Create an LLM instance from a fully flattened LLM config.

        The config must include a ``builder`` key identifying a registered
        LLM builder. All remaining keys are passed directly to the builder
        as keyword arguments.
        """

        builder_name = llm_config.get("builder")
        if not builder_name:
            raise FlotillaConfigurationError(
                "LLM configuration must define a 'builder' field"
            )

        builder = container.get_factory(builder_name)
        if not builder:
            raise FlotillaConfigurationError(
                f"No LLM builder registered for '{builder_name}'"
            )

        # Remove metadata and delegate construction
        kwargs = dict(llm_config)
        # strip out builder and provider from the config
        kwargs.pop("builder", None)
        kwargs.pop("provider", None)

        return builder(**kwargs)

