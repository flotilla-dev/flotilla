
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.tools.tool_registry import ToolRegistry
from flotilla.tools.base_tool_provider import BaseToolProvider
from flotilla.container.component_factory import ComponentBuilder
from flotilla.core.errors import FlotillaConfigurationError

from typing import List


def tool_registry_builder(*, container: FlotillaContainer, tool_provider_names:List[str] ) -> ToolRegistry:
    tool_providers: List[str] = []

    for tool_provider_name in tool_provider_names:
        # check if tool proivder exists
        if not container.exists(tool_provider_name):
            raise FlotillaConfigurationError(f"ToolProvider {tool_provider_name} does not exist in FlotillaContainer")


        provider = container.get(tool_provider_name)

        # If it's a DI provider, calling it returns the instance.
        instance = provider() if callable(provider) else provider

        if not isinstance(instance, BaseToolProvider):
            raise TypeError(
                f"Container attribute '{tool_provider_name}' did not resolve to a BaseToolProvider "
                f"(got {type(instance).__name__})"
            )

        tool_providers.append(instance)

    return ToolRegistry(tool_providers=tool_providers)


ToolRegistryBuilder: ComponentBuilder = tool_registry_builder