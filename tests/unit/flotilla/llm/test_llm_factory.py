import pytest

from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.llm.llm_factory import LLMFactory
from flotilla.flotilla_configuration_error import FlotillaConfigurationError
from flotilla.container.component_builder import ComponentBuilder


# ---------------------------------------------------------------------
# Test builders
# ---------------------------------------------------------------------

def mock_llm_builder(*, model:str, temperature:float):
    # container is container.di, config is flattened llm config
    return {
        "model": model,
        "temperature": temperature
    }


MockLLMBuilder: ComponentBuilder = mock_llm_builder


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------

@pytest.fixture
def container(minimal_settings) -> FlotillaContainer:
    """
    Real FlotillaContainer with minimal settings.
    """
    return FlotillaContainer(settings=minimal_settings)


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------

def test_create_raises_if_builder_missing(container):
    """
    LLMFactory should fail fast if 'builder' is not defined.
    """
    llm_config = {
        "model": "gpt-4",
        "temperature": 0.7,
    }

    with pytest.raises(
        FlotillaConfigurationError,
        match="LLM configuration must define a 'builder' field",
    ):
        LLMFactory.create(container, llm_config)


def test_create_raises_if_builder_not_registered(container):
    """
    LLMFactory should fail fast if the builder name does not
    exist in the container.
    """
    llm_config = {
        "builder": "missing-builder",
        "model": "gpt-4",
    }

    with pytest.raises(
        FlotillaConfigurationError,
        match="No LLM builder registered for 'missing-builder'",
    ):
        LLMFactory.create(container, llm_config)


def test_create_invokes_registered_builder(container):
    """
    LLMFactory should:
    - look up the builder by name
    - call it with container.di and config
    - return the builder's result
    """    
    container.register_builder("mock-llm-builder", MockLLMBuilder)

    llm_config = {
        "builder": "mock-llm-builder",
        "model": "gpt-4",
        "temperature": 0.5,
    }

    llm = LLMFactory.create(container, llm_config)

    assert isinstance(llm, dict)
    assert llm["model"] == "gpt-4"
    assert llm["temperature"] == 0.5


def test_builder_exceptions_are_propagated(container):
    """
    LLMFactory should not swallow exceptions raised by builders.
    """

    def failing_builder():
        raise RuntimeError("builder exploded")

    container.register_builder("failing-builder", failing_builder)

    llm_config = {
        "builder": "failing-builder",
    }

    with pytest.raises(RuntimeError, match="builder exploded"):
        LLMFactory.create(container, llm_config)
