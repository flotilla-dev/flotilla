import importlib
import inspect
import pkgutil
import pathlib
from typing import List, Callable
from config.settings import Settings
from langchain_core.tools import StructuredTool
from config.config_models import ToolRegistryConfig

class ToolRegistry:
    """
    Dynamically discovers and manages all LangChain tools
    defined in configured packages.
    """

    def __init__(self, config:ToolRegistryConfig | None = None):
        if config is None:
            settings = Settings()
            config = settings.get_tool_registry_config()
        
        self.config = config
        self._tools = []
        self._loaded = False


    def _discover_tools(self) -> List:
        """Internal: scans configured packages and loads @tool objects."""
        all_tools = []

        for package_name in self.config.tool_packages:
            package = importlib.import_module(package_name)
            package_path = pathlib.Path(package.__file__).parent

            iterator = (
                pkgutil.walk_packages([str(package_path)], f"{package_name}.")
                if self.config.tool_recursive
                else pkgutil.iter_modules([str(package_path)])
            )

            for _, full_module_name, is_pkg in iterator:
                if is_pkg:
                    continue

                try:
                    module = importlib.import_module(full_module_name)
                except Exception as e:
                    print(f"Skipping {full_module_name}: import failed ({e})")
                    continue

                for _, obj in inspect.getmembers(module):
                    # LangChain tools are StructuredTool
                    if isinstance(obj, StructuredTool):
                        all_tools.append(obj)

        return all_tools


    def load_tools(self, force_reload: bool = False):
        """Load or reload tools from configured packages."""
        if self._loaded and not force_reload:
            return
        self._tools = self._discover_tools()
        self._loaded = True
        print(f"Loaded {len(self._tools)} tools from {self.config.tool_packages}")


    def get_all_tools(self) -> List:
        """Return list of all discovered tools."""
        if not self._loaded:
            self.load_tools()
        return self._tools
    
    def get_tools(self, filter_function: Callable[[StructuredTool], bool]) -> List[StructuredTool]:
        """Returns a list of Tools based on the filter function that was provided"""
        return list(filter(filter_function, self.get_all_tools()))

    def get_tool_names(self) -> List[str]:
        """Return just the names of all tools."""
        return [t.name for t in self.get_all_tools()]
    
    def register_tool(self, tool:StructuredTool):
        """Adds a Tool the internal collection of tools"""
        self._tools.append(tool)

    def unregister_tool(self, name:str):
        """Removes a tool from the internal collection if its name matches the tools name"""
        filtered_toools = [tool for tool in self._tools if tool.name != name]
        self._tools = filtered_toools