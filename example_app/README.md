# Example Application: Weather App

This folder contains a complete example demonstrating how to build an application using the Flotilla framework.

The example shows how to:
- Load and merge environment-based YAML config
- Initialize ToolRegistry and AgentRegistry automatically
- Use `WeatherTools` to call an external API
- Use `WeatherAgent` to interpret queries and respond with structured output
- Run the OrchestrationAgent end-to-end

---

## 🧩 Components

### **WeatherTools**

Implements three tools:
- `get_weather_for_location`
- `get_forecast_for_location`
- `get_user_location`

All tools use configuration from:
```
example_app/config/<env>.yml
```

### **WeatherAgent**

- Provides a weather-specific domain prompt
- Selects weather tools via `tool_filter()`
- Uses a standardized LLM JSON output format
- Parses tool output into structured form

### **main.py**

Entry point that:
1. Loads settings using `ConfigLoader`
2. Creates the OrchestrationAgent
3. Starts the agent system
4. Accepts a user query
5. Routes it to WeatherAgent
6. Prints a `BusinessAgentResponse`

---

## 🚀 Running the Example

From the project root:

```bash
python example_app/src/main.py
```

This will:
- Load configuration from `example_app/config/`
- Discover and configure all tools and agents
- Execute a sample weather query
- Display the structured response

---

## 📁 Structure

```
example_app/
├── config/
│   ├── default.yml        # Base configuration
│   ├── local.yml          # Local overrides
│   ├── uat.yml            # UAT environment
│   └── prod.yml           # Production environment
├── src/
│   ├── main.py            # Application entry point
│   ├── tools/
│   │   └── weather_tools.py
│   └── agents/
│       └── weather_agent.py
└── README.md              # This file
```

---

## 🔧 Configuration

The example uses environment-specific configuration files:

- Set `ENV` environment variable to choose config (defaults to `local`)
- `default.yml` contains all base settings
- Environment files override specific values

Example:
```bash
ENV=uat python example_app/src/main.py
```

---

## 📝 Extending the Example

To add new functionality:

1. **Add a new tool**: Create a new `ToolFactory` subclass in `tools/`
2. **Add a new agent**: Create a new `BaseBusinessAgent` subclass in `agents/`
3. **Update config**: Add tool-specific configuration to `config/default.yml`
4. **Run**: The framework will automatically discover and register your additions