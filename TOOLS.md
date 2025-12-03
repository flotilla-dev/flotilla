# Tools in Flotilla

Flotilla provides a clean, automatic way to define tools that can be used by LLM-powered agents.

Tools are built using two main components:
- **ToolFactory** – defines a group of related tools
- **ToolRegistry** – discovers, configures, and exposes tools to agents

---

## 🏭 ToolFactory

`ToolFactory` is the base class that app developers extend to create tool sets.

### Key Responsibilities

- Accept tool-specific configuration from `Settings`
- Bind `self` into `@tool` functions
- Produce **StructuredTool** objects ready for LLM execution
- Provide optional lifecycle methods (`configure()`, `startup()`, `shutdown()`)

### Example

```python
class WeatherTools(ToolFactory):
    def _configure_tools(self):
        self.api_key = self.config.tool_configuration["WEATHER_API"]["KEY"]
        self.base_url = self.config.tool_configuration["WEATHER_API"]["BASE_URL"]
    
    @tool
    def get_weather_for_location(self, city: str) -> str:
        ...
```

### How ToolFactory Registers Tools

During discovery, the registry calls `configure()`, which:

1. Populates internal state (API keys, URLs, etc.)
2. Auto-scans instance methods decorated with `@tool`
3. Wraps them into `StructuredTool` instances with `self` correctly bound
4. Returns these tools to the registry

No developer needs to manually register tools.

---

## 🗂 ToolRegistry

`ToolRegistry` is created by the `OrchestrationAgent` and receives:
- `ToolRegistryConfig` from `Settings`
- Package paths to search for `ToolFactory` subclasses

### Responsibilities

- Auto-discover all `ToolFactory` subclasses
- Instantiate and configure each factory
- Register all tools they expose
- Provide APIs for:
  - `get_all_tools()`
  - `get_tools(filter_fn)`
  - `shutdown()` for cleanup

### Lifecycle

```
ToolRegistry()
    ↓
Discover ToolFactory subclasses
    ↓
factory.configure(Settings)
    ↓
factory._register_tools()
    ↓
StructuredTool objects created
    ↓
Tools available to agents
```

---

## Filtering Tools for Agents

Agents do NOT get all tools.

Instead, each agent provides a:

```python
def tool_filter(self, tools: List[StructuredTool]) -> List[StructuredTool]:
```

`ToolRegistry` passes tools through this filter before attaching them.

---

## 🧩 Summary

- `ToolFactory` defines tools
- `ToolRegistry` discovers and configures tools
- Tools automatically become `StructuredTool` objects
- Agents select which tools they want via `tool_filter()`
- Everything is configuration-driven