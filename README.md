# Flotilla Framework

Flotilla is a lightweight, configuration-driven framework for building **LLM-powered multi-agent applications**.

It provides a clean architecture for:
- Discovering and configuring tools (`ToolFactory`, `ToolRegistry`)
- Discovering and registering business agents (`BaseBusinessAgent`, `AgentRegistry`)
- Routing user queries to the appropriate agent (`OrchestrationAgent`)
- Maintaining environment-specific application configuration (`ConfigLoader`, YAML hierarchy)

The framework is flexible enough for large enterprise applications, yet simple enough for small AI projects.

---

## ✨ High-Level Architecture

```
main.py (application)
    ↓
ConfigLoader → Settings
    ↓
OrchestrationAgent
    ├── ToolRegistry
    │   └── ToolFactory subclasses → Structured Tools
    │
    └── AgentRegistry
        └── BaseBusinessAgent subclasses → domain agents
```

### At Runtime

1. **Tools** are discovered and configured
2. **Agents** are discovered, configured, and linked to tools
3. The **OrchestrationAgent** receives user queries and forwards them to the appropriate agent
4. Each agent uses its domain prompt and selected tools to respond

---

## 📦 Repository Structure

```
flotilla/
│
├── src/                # Core framework
│   ├── config/         # YAML-based configuration system
│   ├── tools/          # ToolFactory + tool discovery
│   ├── agents/         # AgentRegistry + base agent classes
│   └── ...
│
├── example_app/        # Example application using Flotilla
│   ├── src/main.py
│   ├── config/         # Example app config hierarchy
│   └── README.md
│
└── tests/              # Unit & integration tests
```

---

## 🧩 Major Components

### **Tools**
- Extend `ToolFactory`
- Register tool functions via `@tool` decorator
- Loaded and configured automatically by `ToolRegistry`

### **Agents**
- Extend `BaseBusinessAgent`
- Discovered automatically by `AgentRegistry`
- Select tools via `tool_filter()`
- Produce standardized responses via `BusinessAgentResponse`

### **Configuration System**
- Multi-layered YAML: `default.yml` + environment overrides
- Loaded via `ConfigLoader`
- Merged into a typed `Settings` Pydantic model

---

## 🚀 Example App

The `example_app/` folder demonstrates:
- How to configure Flotilla
- How to implement a domain agent (WeatherAgent)
- How to implement tool sets (WeatherTools)
- How to run an orchestration loop

See [example_app/README.md](example_app/README.md) for details.

---

## 🧪 Tests

The `tests/` folder contains coverage for:
- Config loader & YAML hierarchy
- Tool registration and configuration
- Agent lifecycle
- Orchestration behavior
- Example agent/tool integration