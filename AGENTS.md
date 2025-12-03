# Agents in Flotilla

Flotilla uses a modular agent system to route user queries to the correct domain logic.

Three key components form the agent layer:
- **BaseBusinessAgent**
- **AgentRegistry**
- **BusinessAgentResponse**

---

## 🤖 BaseBusinessAgent

This is the abstract base class that all domain agents must extend (WeatherAgent, FinanceAgent, etc.).

### Responsibilities

- Provide the **domain prompt**
- Select which tools to use via **tool_filter()**
- Accept configuration and override LLM parameters
- Convert LLM/Tool outputs into a structured **BusinessAgentResponse**
- Expose a clean API for:
  - `configure()`
  - `attach_tools()`
  - `startup()`
  - `run_internal_agent(query)`

### Standard Return Format

Every agent returns a standardized object:

```python
class BusinessAgentResponse(BaseModel):
    status: ResponseStatus
    agent_name: str
    query: str
    message: str
    data: dict
    actions: list
    errors: list
    confidence: float
```

This format allows the `OrchestrationAgent` to uniformly interpret any agent's output.

---

## 📚 AgentRegistry

`AgentRegistry` is responsible for:

- Discovering all `BaseBusinessAgent` subclasses
- Instantiating each agent
- Passing agent configuration
- Allowing agents to select tools
- Calling `agent.startup()`
- Registering each agent in an internal lookup table

### Discovery Flow

```
AgentRegistry()
    ↓
Discover BaseBusinessAgent subclasses
    ↓
agent.configure()
    ↓
registry asks for agent.tool_filter()
    ↓
registry passes selected tools via agent.attach_tools()
    ↓
agent.startup()
```

After discovery, all agents are available for routing.

---

## 📤 BusinessAgentResponse

Agents MUST return a standard response with:

- Human message (`message`)
- Structured machine data (`data`)
- Confidence score
- Status (success, error, etc.)
- Optional tool triggers (`actions`)
- Optional error details (`errors`)

This uniform schema allows the orchestrator to:

- Log consistently
- Chain agent responses
- Optionally feed back into LLM
- Send structured output to downstream systems

---

## 🔍 Summary

- `AgentRegistry` discovers and configures all business agents
- `BaseBusinessAgent` provides domain logic and tool selection
- `BusinessAgentResponse` ensures consistent communication across the system