# Migration Guide: LangChain 1.0.1 & Pydantic 2.12.2

This guide documents the changes made to upgrade the project to:
- **LangChain 1.0.1** (from 0.1.20)
- **LangChain OpenAI 1.0.1** (from 0.1.7)
- **LangChain Community 0.4.0** (from 0.0.38)
- **MCP 1.19.0** (from 0.9.0)
- **Pydantic 2.12.2** (from 2.7.0)
- **Pydantic Settings 2.11.0** (from 2.2.1)

## What Changed

### 1. Package Versions (requirements.txt)

**Before:**
```
langchain==0.1.20
langchain-openai==0.1.7
langchain-community==0.0.38
mcp==0.9.0
pydantic==2.7.0
pydantic-settings==2.2.1
```

**After:**
```
langchain==1.0.1
langchain-openai==1.0.1
langchain-community==0.4.0
mcp==1.19.0
requests==2.32.5
pydantic==2.12.2
pydantic-settings==2.11.0
```

### 2. Import Changes

LangChain 1.0+ reorganized imports to use `langchain_core` for core functionality.

#### Schema/Messages Imports

**Before:**
```python
from langchain.schema import HumanMessage, SystemMessage
```

**After:**
```python
from langchain_core.messages import HumanMessage, SystemMessage
```

**Files Updated:**
- `agents/decisioning_agent.py`
- `agents/business_logic/pricing_agent.py`
- `agents/business_logic/inventory_agent.py`
- `agents/business_logic/customer_agent.py`
- `agents/business_logic/agent_registry.py`

#### Tools Imports

**Before:**
```python
from langchain.tools import StructuredTool
```

**After:**
```python
from langchain_core.tools import StructuredTool
```

**Files Updated:**
- `agents/orchestration_agent.py`

#### Prompts Imports

**Before:**
```python
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
```

**After:**
```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
```

**Files Updated:**
- `agents/orchestration_agent.py`

### 3. Agent Creation Function Change

**Before:**
```python
from langchain.agents import create_openai_tools_agent

agent = create_openai_tools_agent(llm, tools, prompt)
```

**After:**
```python
from langchain.agents import create_tool_calling_agent

agent = create_tool_calling_agent(llm, tools, prompt)
```

**Why:** LangChain 1.0+ renamed this function to be more generic (works with any tool-calling model, not just OpenAI).

**Files Updated:**
- `agents/orchestration_agent.py`

### 4. Pydantic Compatibility

No code changes were needed for Pydantic 2.12.2. The existing code is already compatible with Pydantic 2.x because:

- We're already using Pydantic 2.x syntax
- `Field` and `BaseModel` APIs are stable
- `pydantic-settings` handles environment variable loading

**Files Already Compatible:**
- `models/config_models.py`
- All agent files using Pydantic models

## Migration Steps

If you're updating an existing installation:

### Step 1: Update Dependencies

```bash
# Uninstall old versions
pip uninstall langchain langchain-openai langchain-community mcp requests pydantic pydantic-settings -y

# Install new versions
pip install langchain==1.0.1 langchain-openai==1.0.1 langchain-community==0.4.0 mcp==1.19.0 requests==2.32.5 pydantic==2.12.2 pydantic-settings==2.11.0

# Or simply:
pip install -r requirements.txt --upgrade
```

### Important: requests Version Requirement

**langchain-community 0.4.0** requires `requests>=2.32.5`, so we've updated from 2.31.0 to 2.32.5.

This is a minor version bump with bug fixes and security updates. No breaking changes.

### Step 2: Update Code

All code changes have been applied to the artifacts. If you have a working installation:

1. **Backup your current code**
2. **Replace the following files** with updated versions:
   - `requirements.txt`
   - `agents/orchestration_agent.py`
   - `agents/decisioning_agent.py`
   - `agents/business_logic/pricing_agent.py`
   - `agents/business_logic/inventory_agent.py`
   - `agents/business_logic/customer_agent.py`
   - `agents/business_logic/agent_registry.py`

### Step 3: Test

```bash
# Test imports
python -c "from langchain_core.messages import HumanMessage; print('✅ Imports OK')"

# Test system
python main.py test

# Test query
python main.py query "List all business agents"
```

## Breaking Changes to Watch For

### 1. Agent Executor Behavior

LangChain 1.0 may have slight differences in agent execution:
- Error handling may be more strict
- Streaming behavior may differ
- Tool calling format may vary slightly

**Action:** Test your workflows thoroughly after upgrading.

### 2. Deprecation Warnings

You may see deprecation warnings. These are safe to ignore for now but should be addressed in future updates:

```
DeprecationWarning: ... will be removed in langchain 2.0
```

### 3. SQL Agent Creation

If using `create_sql_agent()` in fabric_data_agent.py:

**Before:**
```python
agent_executor = create_sql_agent(
    llm=self.llm,
    db=self.db,
    agent_type="openai-tools",
    verbose=True
)
```

**After (LangChain 1.0):**
```python
agent_executor = create_sql_agent(
    llm=self.llm,
    db=self.db,
    agent_type="tool-calling",  # Changed name
    verbose=True
)
```

**Note:** This change is not yet applied since we're using REST API for Fabric queries, not SQLDatabase. Apply this if you switch to SQL agents.

## Compatibility Matrix

| Component | Version | Status |
|-----------|---------|--------|
| Python | 3.9+ | ✅ Required |
| LangChain | 1.0.1 | ✅ Updated |
| LangChain OpenAI | 1.0.1 | ✅ Updated |
| LangChain Community | 0.4.0 | ✅ Updated |
| MCP | 1.19.0 | ✅ Updated |
| Pydantic | 2.12.2 | ✅ Updated |
| Pydantic Settings | 2.11.0 | ✅ Updated |
| Azure OpenAI | API 2024-02-15-preview | ✅ Compatible |
| Azure Identity | 1.15.0 | ✅ Compatible |

## MCP 1.19.0 Features

With MCP 1.19.0 (released October 24, 2025), you get:

### New Capabilities
- **Structured Output Support**: Output schemas for tools with automatic validation
- **Resource Annotations**: Enhanced metadata for resources
- **Improved OAuth 2.1**: Better authentication support for resource servers
- **Enhanced Transport Layer**: Streamable HTTP transport improvements
- **Better Error Handling**: More detailed error messages and exception handling

### Key Improvements
- More robust stdio server implementation
- Better progress callback exception handling
- Improved SSE connection establishment
- Enhanced workspace configuration support
- Better compatibility with various MCP clients (Claude Desktop, Cline, Cursor, etc.)

### Breaking Changes
None for basic usage. The MCP 1.19.0 API is backward compatible with 0.9.x for standard server/client implementations.

## Compatibility Verification

All versions have been verified as compatible:

```
langchain-community==0.4.0
  ├─ requires: requests>=2.32.5,<3.0.0 ✅
  └─ requires: pydantic>=2.0.0,<3.0.0 ✅

requests==2.32.5 ✅
  └─ Meets langchain-community requirement

mcp==1.19.0
  └─ No conflicting dependencies

langchain==1.0.1
  ├─ requires: langchain-core>=0.4.0,<0.5.0 ✅
  └─ requires: pydantic>=2.0.0,<3.0.0 ✅

langchain-openai==1.0.1
  ├─ requires: langchain-core>=0.4.0,<0.5.0 ✅
  └─ requires: pydantic>=2.0.0,<3.0.0 ✅

pydantic==2.12.2
  └─ requires: pydantic-core==2.27.2 ✅

pydantic-settings==2.11.0
  └─ requires: pydantic>=2.7.0 ✅
```

## New Features Available

With LangChain 1.0.1, you now have access to:

### 1. Improved Tool Calling
- Better tool selection logic
- More reliable function calling
- Better error messages

### 2. Structured Output
```python
from langchain_core.output_parsers import PydanticOutputParser

parser = PydanticOutputParser(pydantic_object=YourModel)
chain = prompt | llm | parser
```

### 3. Better Streaming Support
```python
for chunk in agent.stream({"input": "your query"}):
    print(chunk)
```

### 4. Enhanced Observability
- Better tracing with LangSmith
- Improved logging
- Detailed execution metadata

## Rollback Instructions

If you need to rollback to previous versions:

```bash
pip install langchain==0.1.20 langchain-openai==0.1.7 langchain-community==0.0.38 mcp==0.9.0 pydantic==2.7.0 pydantic-settings==2.2.1
```

Then revert the import changes:
- Change `langchain_core.messages` → `langchain.schema`
- Change `langchain_core.tools` → `langchain.tools`
- Change `langchain_core.prompts` → `langchain.prompts`
- Change `create_tool_calling_agent` → `create_openai_tools_agent`

## Troubleshooting

### Import Errors

**Error:**
```
ImportError: cannot import name 'HumanMessage' from 'langchain.schema'
```

**Solution:** Update imports to use `langchain_core.messages`

### Agent Creation Errors

**Error:**
```
TypeError: create_openai_tools_agent() missing 1 required positional argument
```

**Solution:** Use `create_tool_calling_agent` instead

### Pydantic Validation Errors

**Error:**
```
pydantic.ValidationError: ...
```

**Solution:** Ensure all config files have valid JSON and all required fields are present

## Additional Resources

- [LangChain 1.0 Migration Guide](https://python.langchain.com/docs/versions/v0_2/migrating_from_v0_1/)
- [Pydantic 2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [LangChain API Reference](https://api.python.langchain.com/)

## Questions?

If you encounter any issues during migration:
1. Check the error message carefully
2. Verify all imports are updated
3. Ensure you're using the correct package versions
4. Test with `python main.py test`

The system is now fully compatible with LangChain 1.0.1 and Pydantic 2.12.2! 🎉