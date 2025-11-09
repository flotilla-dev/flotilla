# Business Logic Agents - Quick Start Guide

## What Are Business Logic Agents?

Business Logic Agents are **specialized AI agents** that handle domain-specific business problems. Instead of one generic agent, you have multiple experts that are automatically selected based on what you ask.

Think of it like calling a company:
- Ask about pricing → Pricing specialist answers
- Ask about inventory → Inventory specialist answers  
- Ask about customers → Customer specialist answers

The orchestration system **automatically routes** your question to the right expert!

## How It Works

### 1. You Ask a Question
```bash
python main.py query "Create a markdown strategy for seasonal items"
```

### 2. System Selects Best Agent
The orchestration agent:
1. Checks which agents can handle "markdown" and "seasonal"
2. **Pricing Agent** scores highest (keywords: markdown, pricing, seasonal)
3. Routes query to Pricing Agent

### 3. Specialized Agent Executes
Pricing Agent:
1. Analyzes your query
2. Applies pricing-specific business logic
3. Returns structured recommendations

### 4. You Get Expert Results
```json
{
  "agent": "pricing_agent",
  "domain": "pricing",
  "strategy": "Phased Markdown Strategy",
  "recommendations": [...]
}
```

## Built-In Agents

### 🏷️ Pricing Agent
**Handles**: Price optimization, markdowns, competitive pricing, dynamic pricing

**Try these queries**:
```bash
python main.py query "Optimize prices for slow-moving inventory"
python main.py query "Create a 3-phase markdown strategy for end-of-season items"
python main.py query "How should we price against our competitors?"
python main.py query "Recommend dynamic pricing for peak hours"
```

### 📦 Inventory Agent
**Handles**: Reorder optimization, stock analysis, turnover, safety stock

**Try these queries**:
```bash
python main.py query "Which items should we reorder this week?"
python main.py query "Identify overstocked items"
python main.py query "Calculate safety stock for high-demand products"
python main.py query "How can we improve inventory turnover?"
```

## Creating Your Own Agent

### Step 1: Copy the Template

Copy `agents/business_logic/customer_agent.py` as a starting point:

```bash
cp agents/business_logic/customer_agent.py agents/business_logic/my_agent.py
```

### Step 2: Define Your Agent

```python
class MyAgent(BaseBusinessAgent):
    def __init__(self, llm_config, agent_id="my_agent"):
        super().__init__(agent_id=agent_id, agent_name="My Custom Agent")
        self.llm = self._initialize_llm(llm_config)
    
    def _initialize_capabilities(self):
        """Define what your agent can do"""
        self._capabilities = [
            AgentCapability(
                name="my_capability",
                description="What this does",
                keywords=["keyword1", "keyword2", "keyword3"],
                examples=["Example query 1", "Example query 2"]
            )
        ]
    
    def get_domain(self) -> BusinessDomain:
        return BusinessDomain.OPERATIONS  # or MARKETING, FINANCE, etc.
    
    def can_handle(self, query, context=None):
        """How confident are you about handling this query?"""
        score = 0.0
        for capability in self._capabilities:
            score = max(score, self._match_keywords(query, capability.keywords))
        return score
    
    def execute(self, query, context=None):
        """Your custom business logic"""
        # Add your logic here
        result = {"your": "data"}
        return self._create_result(success=True, data=result)
```

### Step 3: Register Your Agent

In `agents/business_logic/agent_registry.py`, add to `_register_default_agents()`:

```python
def _register_default_agents(self):
    # Existing agents...
    
    # Add your agent
    from agents.business_logic.my_agent import MyAgent
    my_agent = MyAgent(self.llm_config)
    self.register_agent(my_agent)
```

### Step 4: Test It

```bash
python main.py query "your test query with keywords"
```

## Tips for Great Agents

### 1. Choose Specific Keywords
❌ Bad: `["data", "analysis", "report"]` (too generic)  
✅ Good: `["cohort analysis", "customer segmentation", "rfm"]` (specific)

### 2. Don't Overlap Keywords
If two agents have the same keywords, queries will be ambiguous.

**Example - BAD**:
- Pricing Agent: `["price", "cost"]`
- Finance Agent: `["price", "cost"]`  ← Overlap!

**Example - GOOD**:
- Pricing Agent: `["markdown", "sku pricing", "price optimization"]`
- Finance Agent: `["cost analysis", "margin", "profitability"]`

### 3. Return Structured Data
Always return JSON with clear structure:

```python
return self._create_result(
    success=True,
    data={
        "recommendations": [...],
        "rationale": "...",
        "expected_impact": "...",
        "next_steps": [...]
    }
)
```

### 4. Use Appropriate Temperature
```python
# For precise calculations (inventory, finance)
temperature=0.2

# For balanced decisions (pricing, operations)
temperature=0.5

# For creative strategies (marketing, customer engagement)
temperature=0.7
```

## Advanced Usage

### Get Multiple Perspectives

```python
# Execute with ALL agents that can handle the query
results = registry.execute_with_multiple_agents(
    query="How can we improve profitability?",
    min_confidence=0.3
)

# Results will include:
# - Pricing Agent: "Optimize pricing strategy"
# - Inventory Agent: "Reduce carrying costs"
# - etc.
```

### Manual Agent Selection

```python
# Get specific agent by domain
pricing_agent = registry.get_agent_by_domain(BusinessDomain.PRICING)

# Execute directly
result = pricing_agent.execute("Create markdown strategy")
```

### See What's Available

```bash
# List all registered agents
python main.py query "List all business agents"

# Or in code:
agents = registry.list_agents()
for agent in agents:
    print(f"{agent['agent_name']}: {agent['domain']}")
```

## Troubleshooting

### "No suitable agent found"

**Problem**: Your query doesn't match any agent's keywords

**Solutions**:
1. Add more keywords to relevant agent
2. Lower confidence threshold (default is 0.3)
3. Create a new agent for this domain

### Wrong Agent Selected

**Problem**: Query routed to unexpected agent

**Solutions**:
1. Make your query more specific
2. Add negative keywords to exclude certain agents
3. Check for keyword overlap between agents
4. Use `use_llm_router=True` for smarter routing

### Agent Returns Generic Results

**Problem**: Agent not using domain expertise

**Solutions**:
1. Improve the system prompt in agent's `execute()` method
2. Provide more context data
3. Add specific examples in the prompt
4. Lower LLM temperature for more focused responses

## Real-World Example

Let's build a **Promotions Agent** for managing marketing promotions:

```python
# agents/business_logic/promotions_agent.py

class PromotionsAgent(BaseBusinessAgent):
    def __init__(self, llm_config, agent_id="promotions_agent"):
        super().__init__(agent_id=agent_id, agent_name="Promotions Strategy Agent")
        self.llm = self._initialize_llm(llm_config)
    
    def _initialize_capabilities(self):
        self._capabilities = [
            AgentCapability(
                name="promotion_planning",
                description="Plan and optimize promotional campaigns",
                keywords=["promotion", "sale", "campaign", "discount event", "promo"],
                examples=[
                    "Plan Black Friday promotion strategy",
                    "Optimize BOGO promotion for maximum impact"
                ]
            ),
            AgentCapability(
                name="promotion_performance",
                description="Analyze promotion effectiveness",
                keywords=["promotion performance", "promo roi", "campaign results"],
                examples=[
                    "How did our last promotion perform?",
                    "Calculate ROI on recent sales campaign"
                ]
            )
        ]
    
    def get_domain(self):
        return BusinessDomain.MARKETING
    
    def can_handle(self, query, context=None):
        max_score = 0.0
        for cap in self._capabilities:
            score = self._match_keywords(query, cap.keywords)
            max_score = max(max_score, score)
        return max_score
    
    def execute(self, query, context=None):
        system_prompt = """You are a promotions expert. Design data-driven promotional 
        strategies that balance customer acquisition, inventory movement, and profitability."""
        
        user_prompt = f"Query: {query}\n\nContext: {context}"
        
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        return self._create_result(
            success=True,
            data=self._parse_json_response(response.content)
        )
```

Register it:
```python
# In agent_registry.py
from agents.business_logic.promotions_agent import PromotionsAgent

promotions_agent = PromotionsAgent(self.llm_config)
self.register_agent(promotions_agent)
```

Use it:
```bash
python main.py query "Plan a promotion strategy for clearing summer inventory"
# Automatically routed to Promotions Agent!
```

## Next Steps

1. **Try the built-in agents** with different queries
2. **Read** `agents/business_logic/README.md` for detailed docs
3. **Create** your first custom agent
4. **Share** your agent designs with the team!

## Questions?

- See full documentation: `agents/business_logic/README.md`
- Check examples: `agents/business_logic/customer_agent.py`
- Test your setup: `python main.py test`