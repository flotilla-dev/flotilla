# Configuration System

Flotilla uses a hierarchical YAML configuration system with environmental overrides. This allows clean separation of default settings, environment-specific overrides, tool configuration, and agent configuration.

---

## File Structure

Configuration files are located in `example_app/config/`:

```
example_app/config/
├── default.yml
├── local.yml
├── uat.yml
└── prod.yml
```

Each file provides overrides for:
- LLM settings
- Tool registry settings
- Agent registry settings
- Tool-specific configurations (e.g., API keys, base URLs)

---

## How Configuration Merging Works

Flotilla follows this deterministic merge order:

```
default.yml
    ↓ merged with
<ENV>.yml
    ↓ parsed into
Settings (Pydantic model)
```

### Example Usage

```python
settings = ConfigLoader.load("UAT", config_path)
```

### Priority Rules

1. `default.yml` always loads first
2. `<env>.yml` overrides any matching key
3. Any missing keys fall back to defaults
4. Output becomes a strongly typed `Settings` object

---

## Configuration Sections

### LLM Configuration

```yaml
LLM:
  API_KEY: ...
  MODEL: gpt-4o-mini
  TEMPERATURE: 0.1
  TYPE: OPENAI
```

### Tool Registry

```yaml
TOOL_REGISTRY:
  PACKAGES: ["tools"]
  RECURSIVE: true
  ENABLE_DISCOVERY: true
```

### Agent Registry

```yaml
AGENT_REGISTRY:
  PACKAGES: ["agents.business_logic"]
  RECURSIVE: true
  ENABLE_DISCOVERY: true
```

### Tool Configuration

```yaml
TOOL_CONFIGURATION:
  WEATHER_API:
    KEY: ...
    BASE_URL: ...
```

Tool configurations are accessible inside `ToolFactory` via:

```python
self.config.tool_configuration["WEATHER_API"]["BASE_URL"]
```

---

## Environment Overrides

- `default.yml` should define all keys
- Environment files only override values

Example `local.yml`:

```yaml
# local.yml
LLM:
  API_KEY: "sk-local-123"

TOOL_CONFIGURATION:
  WEATHER_API:
    KEY: "test-key"
```

---

## Summary

- Configuration is YAML-driven
- `default.yml` defines the schema
- `<env>.yml` files override defaults
- All merged into a typed `Settings` model
- Settings flow into:
  - `ToolRegistryConfig`
  - `AgentRegistryConfig`
  - Factories and agents