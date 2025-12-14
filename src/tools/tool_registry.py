import importlib
import inspect
import pkgutil
import pathlib
from typing import List, Callable
from langchain_core.tools import StructuredTool
from config.config_models import ToolRegistryConfig
from tools.base_tool_provider import BaseToolProvider
from config.config_factory import ConfigFactory
from utils.logger import get_logger

logger = get_logger(__name__)

class ToolRegistry:
    """
    Dynamically discovers and manages all LangChain tools
    defined in configured packages.
    """

    def __init__(self, config:ToolRegistryConfig):        
        """
        Constructor for the ToolRegistry that is configured via ToolRegistryConfig class.  Use the ConfigFactory to create a new ToolRegistryConfig instance

        Args:
            config:  The ToolRegistryConfig to use with this ToolRegistry
        """
        self.config = config
        self._providers = []
        self._loaded = False
        if self.config.provider_discovery:
            self._discover_tools()

    # -------------------------
    # Interal Tool discovery logic
    # -------------------------

    def _discover_tools(self):
        """Internal: scans configured packages and loads @tool objects."""
        all_tools = []

        for package_name in self.config.provider_packages:
            package = importlib.import_module(package_name)
            package_path = pathlib.Path(package.__file__).parent

            iterator = (
                pkgutil.walk_packages([str(package_path)], f"{package_name}.")
                if self.config.provider_recursive
                else pkgutil.iter_modules([str(package_path)])
            )


                        # Scan submodules
            for _, full_module_name, is_pkg in iterator:
                if not is_pkg:
                    self._load_providers_from_module(full_module_name)

            # Also check the package’s __init__.py
            self._load_providers_from_module(package_name)

        self._loaded = True


    def _load_providers_from_module(self, module_name: str):
        """Import a module and load all ToolProvider subclasses inside it."""
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            logger.warning(f"Skipping {module_name}: import failed ({e})")
            return

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseToolProvider) and obj is not BaseToolProvider:
                try:
                    provider_instance = obj()
                    self.register_provider(provider_instance)
                except Exception as e:
                    logger.error(f"Failed to initialize tool {obj.__name__}: {e}")


    # --------------------------
    # Public API methods
    # --------------------------

    def register_provider(self, provider:BaseToolProvider):
        """Adds a Tool the internal collection of tools"""
        logger.info(f"Register a new concrete ToolProvider {provider.provider_name}")
        config = ConfigFactory.create_tool_config(provider.provider_id, self.config.settings)
        provider.configure(config=config)
        self._providers.append(provider)
        if not self._loaded:
            self._loaded = True

    def unregister_provider(self, name:str):
        """Removes a ToolProvider from the internal collection if its name matches the provider name"""
        logger.info(f"Remove provider {name} from ToolRegistry")
        filtered_toools = [provider for provider in self._providers if provider.provider_name != name]
        self._providers = filtered_toools


    def load_tools(self, force_reload: bool = False):
        """Load or reload providers from configured packages."""
        if self._loaded and not force_reload:
            return
        self._discover_tools()
        logger.info(f"Loaded {len(self._providers)} tools from {self.config.provider_packages}")


    def get_all_tools(self) -> List[StructuredTool]:
        """
        Returns a flattened list of all StructuredTool objects provided
        by every registered ToolProvider instance.
        """
        all_structured_tools: List[StructuredTool] = []

        for provider in self._providers:  # each is a BaseTool
            if isinstance(provider, BaseToolProvider):
                all_structured_tools.extend(provider.tools)

        return all_structured_tools
    
    def get_tools(self, filter_function: Callable[[StructuredTool], bool]) -> List[StructuredTool]:
        """Returns a list of Tools based on the filter function that was provided"""
        return list(filter(filter_function, self.get_all_tools()))

    def get_tool_names(self) -> List[str]:
        """Return just the names of all tools."""
        return [t.name for t in self.get_all_tools()]
    

    def shutdown(self):
        """Lifecycle method to cleanup resources when the application is finished"""
        logger.info("Shutdown the ToolRegistry")
        for tool in self._providers:
            if tool and isinstance(tool, BaseToolProvider):
                logger.debug(f"Calling shutdown on Tool {tool.tool_name}")
                tool.shutdown()
            else:
                logger.warning(f"Non BaseTool in tools {tool}, skipping shutdown call")

