# Orchestration Agent System


## Architecture

```
flotilla/
├── agents/
│   ├── base_business_agent.py    # Base class for all business agents
│   ├── agent_registry.py         # Dynamic agent selection/routing
│   ├── orchestration_agent.py    # Main orchestration logic
│   └── business_logic/           # Specialized business agents
│       └── README.md             # Business agent documentation
├── config/
│   ├── settings.py               # Configuration management
│   └── config_models.py          # Pydantic configuration models
├── llm/
│   └── llm_provider.py           # Factory for creating LLM instance
├── tools/
│   └── tool_registry.py          # Dynamic tool discovery and registration
├── utils/
│   └── logger.py                 # Logging utilities
├── main.py                       # CLI entry point
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Features

### 🎯 Business Logic Agents (Dynamic Selection)
- **Multiple specialized agents** for different business domains
- **Automatic agent selection** based on query content
- **Extensible**: Easy to add custom agents for your business needs
- **Intelligent routing**: Keyword matching + optional LLM-based selection

### 🎯 Orchestration Agent
- Coordinates all sub-agents
- Natural language query processing
- Workflow execution
- Tool-based agent architecture

## Installation

### Prerequisites
- Python 3.9+

### Setup

1. **Clone and install dependencies:**
```bash
git clone <repository-url>
cd orchestration_system
pip install -r requirements.txt
```

2. **Initialize configuration:**
```bash
python main.py init
```

3. **Update configuration files** in `config/` directory:

**`config/client_config.json`:**
```json
{
  "client_id": "client_001",
  "client_name": "Your Company",
  "fabric_workspace": {
    "workspace_id": "YOUR_WORKSPACE_ID",
    "lakehouse_id": "YOUR_LAKEHOUSE_ID",
    "lakehouse_name": "sales_analytics",
    "endpoint": "https://api.fabric.microsoft.com/v1",
    "tenant_id": "YOUR_TENANT_ID"
  },
  "metadata": {
    "industry": "retail",
    "region": "north_america"
  }
}
```

**`config/azure_openai_config.json`:**
```json
{
  "endpoint": "https://YOUR_RESOURCE.openai.azure.com/",
  "api_key": "YOUR_API_KEY",
  "api_version": "2024-02-15-preview",
  "deployment_name": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 2000
}
```

**`config/block_mcp_config.json`:**
```json
{
  "server_command": "npx",
  "server_args": ["-y", "@modelcontextprotocol/server-square"],
  "access_token": "YOUR_SQUARE_ACCESS_TOKEN",
  "environment": "sandbox",
  "timeout": 30
}
```

4. **Optional: Set environment variables** (overrides config files):
```bash
export AZURE_OPENAI_ENDPOINT="https://..."
export AZURE_OPENAI_API_KEY="..."
export BLOCK_ACCESS_TOKEN="..."
```

## Usage

### CLI Commands

#### Initialize Configuration
```bash
python main.py init
```

#### Execute a Query
```bash
python main.py query "What were the top 5 products by sales last month?"
```

#### Test System Components
```bash
python main.py test
```

#### Interactive Mode
```bash
python main.py interactive
```

#### Execute a Workflow
```bash
python main.py workflow workflows/pricing_optimization.json
```

#### Display System Information
```bash
python main.py info
```

### Example Queries

**Data Analysis:**
```bash
python main.py query "Show me total sales by category for Q4 2024"
```

**Decision Making:**
```bash
python main.py query "Create a decision tree for markdown pricing based on inventory levels and sales velocity"
```

**Price Updates:**
```bash
python main.py query "Update the price of item XYZ to $19.99"
```

**Combined Operations:**
```bash
python main.py query "Analyze sales for slow-moving items and recommend price adjustments"
```

**Business Logic Agents:**
```bash
# Pricing optimization
python main.py query "Create a markdown strategy for seasonal items"

# Inventory management
python main.py query "Which items should we reorder this week?"

# List available agents
python main.py query "What business logic agents are available?"
```

### Workflow Example

Create a workflow file `workflows/pricing_optimization.json`:

```json
{
  "name": "Pricing Optimization Workflow",
  "description": "Analyze sales data and optimize pricing",
  "steps": [
    {
      "name": "get_sales_data",
      "type": "query_data",
      "config": {
        "query": "Get sales data for items with inventory over 100 units"
      }
    },
    {
      "name": "create_pricing_decision",
      "type": "create_decision",
      "config": {
        "context": "Optimize pricing for slow-moving inventory",
        "criteria": [
          "Sales velocity",
          "Current inventory level",
          "Historical price elasticity"
        ],
        "data_source": "get_sales_data"
      }
    },
    {
      "name": "evaluate_pricing",
      "type": "evaluate_decision",
      "config": {
        "decision_source": "create_pricing_decision",
        "data_source": "get_sales_data"
      }
    },
    {
      "name": "update_prices",
      "type": "update_prices",
      "config": {
        "items": [
          {
            "item_id": "ITEM_001",
            "new_price": 14.99
          }
        ]
      }
    }
  ]
}
```

Execute the workflow:
```bash
python main.py workflow workflows/pricing_optimization.json
```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | From config |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | From config |
| `BLOCK_ACCESS_TOKEN` | Square API access token | From config |
| `LOG_LEVEL` | Logging level | INFO |
| `ENABLE_TRACING` | Enable request tracing | true |
| `MAX_RETRIES` | Maximum retry attempts | 3 |

### Azure Fabric Authentication

The system uses Azure `DefaultAzureCredential` which supports:
- Environment variables
- Managed Identity
- Azure CLI authentication
- Visual Studio authentication
- Interactive browser authentication

Ensure you're authenticated to Azure before running:
```bash
az login
```

## Development

### Project Structure

- **agents/** - Agent implementations
  - **business_logic/** - Specialized domain agents with dynamic routing
- **clients/** - External service clients
- **config/** - Configuration management
- **models/** - Data models and schemas
- **utils/** - Utility functions
- **workflows/** - Workflow definitions

### Adding Business Logic Agents

Business logic agents are automatically selected based on query content. See `agents/business_logic/README.md` for detailed instructions.

**Quick Start:**

1. Create new agent class inheriting from `BaseBusinessAgent`
2. Define capabilities with keywords
3. Implement `can_handle()` and `execute()` methods
4. Register in `agent_registry.py`

Example:
```python
from agents.business_logic.base_business_agent import BaseBusinessAgent

class MarketingAgent(BaseBusinessAgent):
    def _initialize_capabilities(self):
        self._capabilities = [
            AgentCapability(
                name="campaign_optimization",
                keywords=["campaign", "marketing", "roi"]
            )
        ]
    
    def can_handle(self, query, context=None):
        return self._match_keywords(query, ["campaign", "marketing"])
    
    def execute(self, query, context=None):
        # Your business logic here
        pass
```

Then register it:
```python
# In agent_registry.py _register_default_agents()
marketing_agent = MarketingAgent(self.llm_config)
self.register_agent(marketing_agent)
```

### Adding New Agents

1. Create agent class in `agents/`
2. Implement required methods
3. Add tools to `OrchestrationAgent._create_tools()`
4. Update configuration models if needed

### Adding New Workflows

Create a JSON workflow file with steps:
- `query_data` - Query lakehouse
- `create_decision` - Create decision tree
- `evaluate_decision` - Evaluate decision
- `update_prices` - Update POS prices

## Troubleshooting

### Common Issues

**Authentication Errors:**
- Verify Azure credentials: `az login`
- Check API keys in configuration files
- Ensure proper permissions on Fabric workspace

**MCP Server Issues:**
- Verify Node.js is installed: `node --version`
- Check Square access token is valid
- Review MCP server logs in stderr

**Query Failures:**
- Validate lakehouse connection and permissions
- Check schema information: `python main.py test`
- Review natural language query clarity

### Logs

Enable debug logging:
```bash
python main.py --log-level DEBUG query "your query"
```

## Security

- Store credentials in environment variables or Azure Key Vault
- Use `.env` file for local development (add to `.gitignore`)
- Never commit API keys or access tokens
- Use Azure Managed Identity in production

## License

[Your License Here]

## Support

For issues and questions:
- Check the troubleshooting section
- Review logs with `--log-level DEBUG`
- Contact support team

## Roadmap

- [ ] Add support for multiple lakehouses per client
- [ ] Implement caching for frequently accessed data
- [ ] Add webhook support for real-time POS events
- [ ] Expand decision tree persistence options
- [ ] Add monitoring and metrics dashboard
- [ ] Multi-agent collaboration on complex queries
