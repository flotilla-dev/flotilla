from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.flotilla_configuration_error import FlotillaConfigurationError


class LLMFactory:

    @staticmethod
    def create(container: FlotillaContainer, llm_config: dict):
        """
        Create an LLM instance from a fully flattened LLM config.

        Expected llm_config shape:
        - contains a 'builder' key
        - other keys are provider / model specific
        """

        builder_name = llm_config.get("builder")
        if not builder_name:
            raise FlotillaConfigurationError(
                "LLM configuration must define a 'builder' field"
            )

        builder = container.get_builder(builder_name)
        if not builder:
            raise FlotillaConfigurationError(
                f"No LLM builder registered for '{builder_name}'"
            )

        # Delegate construction to the builder
        return builder(container=container.di, config=llm_config)
