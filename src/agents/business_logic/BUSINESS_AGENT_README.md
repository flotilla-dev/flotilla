# Business Logic Agents

This directory contains specialized business logic agents that can be dynamically selected at runtime by the orchestration engine based on input queries.

## Architecture

The business agent system uses a **registry pattern** with **dynamic routing**:

1. **Base Agent** (`base_business_agent.py`) - Abstract base class all agents inherit from
2. **Agent Registry** (`agent_registry.py`) - Manages and routes queries to appropriate agents
3. **Specialized Agents** - Domain-specific agents (pricing, inventory, customer, etc.)

## How It Works

### 1. Agent Selection

When a query comes in, the orchestration engine:

1. **Keyword Matching**: Each agent calculates a confidence score based on keywords in the query
2. **LLM Routing** (optional): Uses GPT-4 to intelligently select the best agent
3. **Threshold Checking**: Only agents meeting the minimum confidence threshold are considered
4. **Execution**: The selected agent executes its specialized business logic

### 2. Agent Confidence Scoring

Each agent implements a `can_handle()` method that returns a confidence score (0.0 to 1.0):

```python
def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
    # Match keywords from agent capabilities
    score = self._match_keywords(query, self.keywords)
    
    # Boost score based on context
    if context and "relevant_data" in context:
        score = min(score + 0.2, 1.0)
    
    return score
```

## Available Agents

### 1. Pricing Agent (`pricing_agent.py`)
**Domain**: Pricing  
**Specializations**:
- Price optimization
- Competitive pricing analysis
- Markdown strategies
- Dynamic pricing

**Keywords**: price, pricing, optimize, discount, markdown, competitive, clearance, promotion

**Example Queries**:
- "Optimize prices for slow-moving inventory"
- "Create a markdown strategy for end-of-season items"
- "How do our prices compare to competitors?"

### 2. Inventory Agent (`inventory_agent.py`)
**Domain**: Inventory  
**Specializations**:
- Reorder optimization
- Stock level analysis
- Turnover optimization
- Safety stock calculation

**Keywords**: reorder, stock, inventory, replenish, turnover, velocity, overstock, understock

**Example Queries**:
- "When should we reorder these items?"
- "Which items are overstocked?"
- "Calculate safety stock for high-demand items"

### 3. Customer Agent (`customer_agent.py`) - EXAMPLE
**Domain**: Customer  
**Specializations**:
- Customer segmentation
- Retention strategies
- Lifetime value analysis

**Keywords**: customer, segment, retention, churn, loyalty, lifetime value

**Example Queries**:
- "Segment customers by purchase behavior"
- "Create a retention strategy for at-risk customers"

## Creating Custom Agents

### Step 1: Create Agent Class

Create a new file in `agents/business_logic/` (e.g., `marketing_agent.py`):

```python
from agents.business_logic.base_business_agent import (
    BaseBusinessAgent,
    BusinessDomain,
    AgentCapability
)
from models.config_models import AzureOpenAIConfig

class MarketingAgent(BaseBusinessAgent):
    def __init__(self, llm_config: AzureOpenAIConfig, agent_id: str = "marketing_agent"):
        super().__init__(agent_id=agent_id, agent_name="Marketing Strategy Agent")
        self.llm = self._initialize_llm(llm_config)
    
    def _initialize_llm(self, config: AzureOpenAIConfig):
        # Initialize your LLM with appropriate temperature
        pass
    
    def _initialize_capabilities(self):
        """Define what your agent can do"""
        self._capabilities = [
            AgentCapability(
                name="campaign_optimization",
                description="Optimize marketing campaigns",
                keywords=["campaign", "marketing", "optimize", "roi"],
                examples=["Optimize email campaign performance"]
            )
        ]
    
    def get_domain(self) -> BusinessDomain:
        return BusinessDomain.MARKETING
    
    def can_handle(self, query: str, context=None) -> float:
        """Calculate confidence score"""
        max_score = 0.0
        for capability in self._capabilities:
            score = self._match_keywords(query, capability.keywords)
            max_score = max(max_score, score)
        return max_score
    
    def execute(self, query: str, context=None):
        """Implement your business logic"""
        # Your custom logic here
        return self._create_result(
            success=True,
            data={"result": "your data"}
        )
```

### Step 2: Register Agent

Option A: **Auto-register** in `agent_registry.py`:

```python
def _register_default_agents(self):
    # Existing agents...
    pricing_agent = PricingAgent(self.llm_config)
    self.register_agent(pricing_agent)
    
    # Add your new agent
    from agents.business_logic.marketing_agent import MarketingAgent
    marketing_agent = MarketingAgent(self.llm_config)
    self.register_agent(marketing_agent)
```

Option B: **Manually register** at runtime:

```python
from agents.business_logic.marketing_agent import MarketingAgent

# In your application code
marketing_agent = MarketingAgent(llm_config)
orchestration_agent.business_registry.register_agent(marketing_agent)
```

### Step 3: Test Your Agent

```bash
# Test agent selection
python main.py query "Optimize our email marketing campaign"

# View available agents
python main.py query "List all available business agents"
```

## Usage Examples

### Using Orchestration Agent

```python
from agents.orchestration_agent import OrchestrationAgent

# Initialize
agent = OrchestrationAgent(config)

# Query automatically routes to best agent
result = agent.execute("Optimize prices for slow-moving items")

# The orchestration agent will:
# 1. Detect this is a pricing query
# 2. Route to PricingAgent
# 3. Execute pricing logic
# 4. Return results
```

### Direct Registry Usage

```python
from agents.business_logic.agent_registry import BusinessAgentRegistry

# Initialize registry
registry = BusinessAgentRegistry(llm_config)

# Execute with automatic agent selection
result = registry.execute_with_best_agent(
    query="Which items should we reorder?",
    context={"inventory_data": {...}}
)

# List