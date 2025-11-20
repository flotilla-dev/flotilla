# Business Logic Agents - Quick Start Guide

## What Are Business Logic Agents?

Business Logic Agents are **specialized AI agents** that handle domain-specific business problems. Each agent inherits from `BaseBusinessAgent` and implements custom business logic while maintaining a standardized interface with the orchestration system.

Think of it like calling a company:
- Ask about pricing → Pricing specialist answers
- Ask about inventory → Inventory specialist answers  
- Ask about customers → Customer specialist answers

The orchestration system **automatically routes** your question to the right expert based on keyword matching and confidence scores!

## How It Works

### 1. You Ask a Question
```bash
python main.py query "Create a markdown strategy for seasonal items"
```

### 2. System Selects Best Agent
The orchestration system:
1. Calls `can_handle()` on each registered agent
2. Each agent scores the query based on keyword matching
3. **Pricing Agent** returns highest confidence (keywords: markdown, pricing, seasonal)
4. Routes query to Pricing Agent

### 3. Specialized Agent Executes
Pricing Agent's `execute()` method:
1. Analyzes your query
2. Applies pricing-specific business logic
3. Returns a standardized `BusinessAgentResponse`

### 4. You Get Expert Results
```json
{
  "status": "success",
  "agent_name": "pricing_agent",
  "query": "Create a markdown strategy for seasonal items",
  "confidence": 0.95,
  "message": "Strategy created successfully",
  "data": {
    "strategy": "Phased Markdown Strategy",
    "recommendations": [...]
  }
}
```

## Agent Lifecycle

Every business agent goes through the following lifecycle:

```
┌─────────────┐
│   Created   │ Agent instantiated with agent_id and agent_name
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│ configure(config)                   │ AgentRegistry calls this
│ - Sets self.config                  │ - Initialize capabilities
│ - Creates LLM instance              │ - Process custom config
│ - Calls _initialize_capabilities()  │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ attach_tools(tools)                 │ Tools filtered and attached
│ - Sets self.tools to available list │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ startup()                           │ Called before first use
│ - Creates internal LangChain agent  │ - Combines prompts
│ - Sets self.started = True          │ - Ready for queries
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ execute(query, context)             │ Process user queries
│ - Returns BusinessAgentResponse     │ - Called repeatedly
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ shutdown()                          │ Cleanup when done
└─────────────────────────────────────┘
```

## Creating Your Own Agent

### Step 1: Copy the Template

Use an existing agent as your starting point:

```bash
cp agents/business_logic/customer_agent.py agents/business_logic/my_agent.py
```

### Step 2: Define Your Agent Class

```python
from typing import List, Optional, Dict, Any
from agents.business_logic.base_business_agent import BaseBusinessAgent, AgentCapability
from agents.business_agent_response import BusinessAgentResponse
from langchain_core.messages import SystemMessage, HumanMessage

class MyAgent(BaseBusinessAgent):
    def __init__(self, llm_config, agent_id="my_agent"):
        super().__init__(agent_id=agent_id, agent_name="My Custom Agent")
        self.llm_config = llm_config
    
    def _initialize_capabilities(self) -> List[AgentCapability]:
        """Define what your agent can do"""
        return [
            AgentCapability(
                name="my_capability",
                description="Handles specific business problems",
                keywords=["keyword1", "keyword2", "keyword3"],
                examples=[
                    "Example query 1",
                    "Example query 2"
                ]
            )
        ]
    
    def get_agent_domain_prompt(self) -> str:
        """Return domain-specific instructions for your agent"""
        return """You are a specialized agent for [your domain].
        
        Your responsibilities:
        - Analyze queries related to [domain]
        - Apply business logic for [specific problems]
        - Return structured recommendations
        
        Always validate inputs and provide confidence scores."""
    
    def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> BusinessAgentResponse:
        """Execute your custom business logic"""
        try:
            # Your business logic here
            result = self._process_query(query, context)
            
            return self.build_success_response(
                query=query,
                data=result,
                message="Analysis complete",
                confidence=0.95
            )
        except Exception as e:
            return self.build_error_response(
                query=query,
                error_code="PROCESSING_FAILED",
                error_details=str(e),
                message="Failed to process query"
            )
    
    def _process_query(self, query: str, context: Optional[Dict]) -> dict:
        """Your custom business logic implementation"""
        # Add your logic here
        return {"your": "data"}
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

## Understanding Agent Selection

### The `can_handle()` Method

Every agent implements `can_handle()` to indicate how confident it is about handling a query:

```python
def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
    """
    Returns confidence score between 0.0 and 1.0
    - 1.0 = Definitely can handle this
    - 0.5 = Might be able to handle this
    - 0.0 = Cannot handle this
    """
```

The default implementation matches keywords from all capabilities:

```python
max_score = 0.0
for capability in self._capabilities:
    score = self._match_keywords(query, capability.keywords)
    max_score = max(max_score, score)
return max_score
```

You can override this for custom matching logic:

```python
def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
    score = super().can_handle(query, context)  # Get default score
    
    # Boost score if context indicates this is our domain
    if context and context.get("domain") == "my_domain":
        score += 0.2
    
    return min(score, 1.0)  # Cap at 1.0
```

## Response Format

All agents return a standardized `BusinessAgentResponse`:

```python
{
    "status": "success" | "error" | "warning" | "failure",
    "agent_name": "your_agent_name",
    "query": "the original user query",
    "confidence": 0.0 to 1.0,
    "message": "Brief human-readable summary",
    "data": {
        # Your domain-specific structured data
        "recommendations": [...],
        "rationale": "...",
        "metrics": {...}
    },
    "actions": [
        # Optional: Next actions for orchestration
    ],
    "errors": [
        # Optional: Error details if status != success
    ]
}
```

Use the response builders:

```python
# Success response
return self.build_success_response(
    query=query,
    data={"key": "value"},
    message="Success message",
    confidence=0.95,
    actions=[{"action": "next_step"}]
)

# Error response
return self.build_error_response(
    query=query,
    error_code="ERROR_CODE",
    error_details="Details about the error",
    message="Error message"
)
```

## Working with Tools

Agents can access tools through the `self.tools` list. By default, all registered tools are available. To restrict which tools your agent can access:

```python
def filter_tools(self, tool: StructuredTool) -> bool:
    """
    Return True to include tool, False to exclude.
    Called during agent registration.
    """
    # Only include tools with "inventory" in the name
    return "inventory" in tool.name.lower()
```

Once tools are attached in the `attach_tools()` lifecycle call, use them in your `execute()` method:

```python
def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> BusinessAgentResponse:
    if self.tools:
        # Call tools as needed via self.run_internal_agent()
        return self.run_internal_agent(query, context)
    else:
        # Execute without tools
        pass
```

## Using the LLM

Your agent has access to an LLM via `self.llm`. Two main approaches:

### Direct LLM Call

```python
from langchain_core.messages import SystemMessage, HumanMessage

def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> BusinessAgentResponse:
    system_prompt = "You are an expert in [domain]..."
    user_prompt = f"Query: {query}\n\nContext: {context}"
    
    return self.llm_call(
        messages=[
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ],
        query=query,
        confidence=0.9,
        extract_json=True  # Automatically parse JSON response
    )
```

### Internal LangChain Agent

If you set up the internal agent with tools:

```python
def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> BusinessAgentResponse:
    return self.run_internal_agent(
        query=query,
        context=context,
        confidence=0.9
    )
```

## Tips for Great Agents

### 1. Choose Specific Keywords

❌ Bad: `["data", "analysis", "report"]` (too generic)  
✅ Good: `["cohort analysis", "customer segmentation", "rfm"]` (specific)

### 2. Avoid Keyword Overlap

If two agents have identical keywords, query routing becomes ambiguous.

**Example - BAD**:
```python
# Pricing Agent
keywords=["price", "cost", "markdown"]

# Finance Agent  
keywords=["price", "cost", "profitability"]  # Overlap!
```

**Example - GOOD**:
```python
# Pricing Agent
keywords=["markdown", "sku pricing", "dynamic pricing"]

# Finance Agent
keywords=["cost analysis", "margin", "revenue impact"]  # Clear distinction
```

### 3. Return Structured Data

Always return well-organized data:

```python
return self.build_success_response(
    query=query,
    data={
        "recommendations": [...],
        "rationale": "Why these recommendations",
        "expected_impact": "What to expect",
        "next_steps": ["Action 1", "Action 2"]
    },
    confidence=0.95
)
```

### 4. Implement Custom `can_handle()` Logic

Go beyond keyword matching when needed:

```python
def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
    # Start with keyword matching
    base_score = super().can_handle(query, context)
    
    # Add domain intelligence
    if self._detect_emergency(query):
        return 1.0  # Handle with high confidence
    
    if context and context.get("requires_approval"):
        return 0.0  # Cannot handle approval workflows
    
    return base_score
```

## Common Patterns

### Pattern 1: LLM-Powered Analysis

```python
class AnalysisAgent(BaseBusinessAgent):
    def _initialize_capabilities(self):
        return [
            AgentCapability(
                name="analysis",
                description="Analyze business data",
                keywords=["analyze", "trend", "insight"],
                examples=["Analyze Q3 sales trends"]
            )
        ]
    
    def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> BusinessAgentResponse:
        return self.llm_call(
            messages=[
                SystemMessage(content="You are a data analyst..."),
                HumanMessage(content=f"Analyze: {query}")
            ],
            query=query,
            confidence=0.85
        )
```

### Pattern 2: Tool-Using Agent

```python
class OptimizationAgent(BaseBusinessAgent):
    def _initialize_capabilities(self):
        return [
            AgentCapability(
                name="optimization",
                description="Optimize business metrics",
                keywords=["optimize", "improve", "efficiency"],
                examples=["Optimize inventory levels"]
            )
        ]
    
    def filter_tools(self, tool: StructuredTool) -> bool:
        return "optimization" in tool.name.lower()
    
    def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> BusinessAgentResponse:
        return self.run_internal_agent(
            query=query,
            context=context,
            confidence=0.9
        )
```

### Pattern 3: Context-Aware Agent

```python
class ContextualAgent(BaseBusinessAgent):
    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        base_score = super().can_handle(query, context)
        
        # Boost confidence if context matches our domain
        if context and context.get("domain") == self.domain:
            base_score = min(base_score + 0.3, 1.0)
        
        return base_score
    
    def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> BusinessAgentResponse:
        domain_context = context or {}
        
        return self.build_success_response(
            query=query,
            data=self._analyze_with_context(query, domain_context),
            confidence=0.9
        )
    
    def _analyze_with_context(self, query: str, context: Dict) -> dict:
        # Use context to enhance analysis
        return {}
```

## Troubleshooting

### "No suitable agent found"

**Problem**: Your query doesn't match any agent's keywords

**Solutions**:
1. Check agent keywords: `python main.py query "List all business agents"`
2. Add more specific keywords to relevant agents
3. Create a new agent for this domain
4. Override `can_handle()` to add custom matching logic

### Wrong Agent Selected

**Problem**: Query routed to unexpected agent

**Solutions**:
1. Make your query more specific and domain-focused
2. Review keyword overlap between agents
3. Implement custom `can_handle()` logic for better scoring
4. Use context to differentiate similar queries

### Agent Returns Generic Results

**Problem**: Agent not using domain expertise

**Solutions**:
1. Improve the system prompt via `get_agent_domain_prompt()`
2. Provide more specific examples in capabilities
3. Use `extract_json=True` in `llm_call()` for structured outputs
4. Pass relevant context to `execute()` method
5. Adjust LLM temperature (0.2 for precise work, 0.7 for creative)

### Lifecycle Not Completing

**Problem**: Agent not ready after startup

**Solutions**:
1. Ensure `_initialize_capabilities()` returns a list of `AgentCapability` objects
2. Verify LLM configuration is correct
3. Check that `configure()` completes without errors
4. Review `_process_agent_configuration()` for custom setup logic

## Complete Example: Building a Recommendation Agent

```python
# agents/business_logic/recommendation_agent.py

from typing import List, Optional, Dict, Any
from agents.business_logic.base_business_agent import BaseBusinessAgent, AgentCapability
from agents.business_agent_response import BusinessAgentResponse
from langchain_core.messages import SystemMessage, HumanMessage

class RecommendationAgent(BaseBusinessAgent):
    def __init__(self, llm_config, agent_id="recommendation_agent"):
        super().__init__(agent_id=agent_id, agent_name="Recommendation Engine")
        self.llm_config = llm_config
    
    def _initialize_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="personalized_recommendations",
                description="Generate personalized product recommendations",
                keywords=["recommend", "suggest", "personalized", "for customer"],
                examples=[
                    "What should we recommend to frequent buyers?",
                    "Generate recommendations based on purchase history"
                ]
            ),
            AgentCapability(
                name="cross_sell",
                description="Identify cross-sell and upsell opportunities",
                keywords=["cross-sell", "upsell", "bundle", "complementary"],
                examples=[
                    "What items cross-sell well together?",
                    "Identify upsell opportunities for premium customers"
                ]
            )
        ]
    
    def get_agent_domain_prompt(self) -> str:
        return """You are a recommendation engine expert. Your role is to:
        - Identify patterns in customer behavior
        - Suggest relevant products based on preferences
        - Calculate recommendation confidence scores
        - Explain reasoning for recommendations
        
        Always return actionable, data-driven suggestions."""
    
    def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> BusinessAgentResponse:
        try:
            result = self.llm_call(
                messages=[
                    SystemMessage(content=self.get_agent_domain_prompt()),
                    HumanMessage(content=f"Query: {query}\n\nContext: {context}")
                ],
                query=query,
                confidence=0.88,
                extract_json=True
            )
            return result
        except Exception as e:
            return self.build_error_response(
                query=query,
                error_code="RECOMMENDATION_FAILED",
                error_details=str(e),
                message="Failed to generate recommendations"
            )
```

Register it in `agent_registry.py`:

```python
from agents.business_logic.recommendation_agent import RecommendationAgent

recommendation_agent = RecommendationAgent(self.llm_config)
self.register_agent(recommendation_agent)
```

Use it:

```bash
python main.py query "What should we recommend to our VIP customers?"
# Automatically routed to Recommendation Agent!
```

## Next Steps

1. **Review the base class**: Read `base_business_agent.py` to understand the full API
2. **Study existing agents**: Check `customer_agent.py` for implementation patterns
3. **Create your first agent**: Follow the template in Step 2 above
4. **Test thoroughly**: Use different queries to validate keyword matching and `can_handle()` scoring
5. **Optimize**: Fine-tune keywords and system prompts for your domain
6. **Share**: Contribute your agent back to the team!

## API Reference

### BaseBusinessAgent Methods

**Lifecycle Methods**:
- `configure(config)` - Initialize agent with config
- `startup()` - Prepare agent for use
- `shutdown()` - Clean up resources
- `attach_tools(tools)` - Attach available tools
- `filter_tools(tool)` - Select which tools to use

**Execution Methods**:
- `execute(query, context)` - Main entry point for queries
- `can_handle(query, context)` - Return confidence score (0.0-1.0)

**Response Builders**:
- `build_success_response(query, data, message, confidence, actions)`
- `build_error_response(query, error_code, error_details, message)`

**LLM Helpers**:
- `llm_call(messages, query, confidence, extract_json)` - Direct LLM call
- `run_internal_agent(query, context, confidence)` - Use internal LangChain agent

**Agent Info**:
- `get_capabilities()` - List agent capabilities
- `get_keywords()` - All agent keywords
- `get_info()` - Full agent information

## Questions?

- See full documentation: `agents/business_logic/README.md`
- Check base class: `agents/business_logic/base_business_agent.py`
- Review response model: `business_agent_response.py`
- Test your setup: `python main.py test`