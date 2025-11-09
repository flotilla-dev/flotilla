# Test Suite Documentation

This directory contains the test suite for the orchestration system.

## Overview

The tests focus on core orchestration logic and exclude external dependencies like:
- Fabric Data Agent (external API)
- Block MCP Client (external service)
- Business Logic Agents (domain-specific implementations)

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── test_config_models.py          # Configuration model tests
├── test_config_loader.py          # Configuration loading tests
├── test_decisioning_agent.py      # Decision tree agent tests
├── test_agent_registry.py         # Agent registry and routing tests
├── test_base_business_agent.py    # Base business agent tests
└── README.md                      # This file
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Registry tests
pytest -m registry

# Decisioning agent tests
pytest -m decisioning

# Configuration tests
pytest -m config
```

### Run Specific Test Files

```bash
# Test configuration models
pytest tests/test_config_models.py

# Test agent registry
pytest tests/test_agent_registry.py

# Test decisioning agent
pytest tests/test_decisioning_agent.py
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov

# Generate HTML coverage report
pytest --cov --cov-report=html

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Run Verbose Mode

```bash
pytest -v
```

### Run Specific Test

```bash
pytest tests/test_agent_registry.py::TestBusinessAgentRegistry::test_register_agent
```

## Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.registry` - Agent registry tests
- `@pytest.mark.decisioning` - Decisioning agent tests
- `@pytest.mark.orchestration` - Orchestration agent tests
- `@pytest.mark.config` - Configuration tests

## Test Coverage

Current test coverage focuses on:

### ✅ Covered Components

1. **Configuration Models** (`models/config_models.py`)
   - All Pydantic models
   - Validation rules
   - Default values

2. **Configuration Loader** (`config/config_loader.py`)
   - JSON file loading
   - Environment variable overrides
   - Sample config generation

3. **Decisioning Agent** (`agents/decisioning_agent.py`)
   - Decision tree creation
   - Decision evaluation
   - Tree refinement
   - JSON parsing

4. **Agent Registry** (`agents/business_logic/agent_registry.py`)
   - Agent registration/unregistration
   - Agent selection (keyword-based)
   - Agent selection (LLM-based)
   - Multi-agent execution
   - Domain-based retrieval

5. **Base Business Agent** (`agents/business_logic/base_business_agent.py`)
   - Abstract base functionality
   - Capability system
   - Keyword matching
   - Result formatting

### 🚫 Not Covered (By Design)

1. **Fabric Data Agent** - External Azure API dependency
2. **Block MCP Client** - External service dependency
3. **Specific Business Logic Agents** - Domain-specific implementations
4. **Orchestration Agent** - Depends on external agents
5. **Main CLI** - Integration level testing

## Writing New Tests

### Test File Naming

- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Using Fixtures

Common fixtures are available in `conftest.py`:

```python
def test_example(mock_azure_openai_config, mock_llm):
    # Use fixtures
    agent = MyAgent(config=mock_azure_openai_config)
    agent.llm = mock_llm
    # Test logic
```

### Mocking LLM Calls

```python
from unittest.mock import Mock, MagicMock

def test_with_mocked_llm(decisioning_agent):
    # Mock LLM response
    mock_response = MagicMock()
    mock_response.content = '{"key": "value"}'
    decisioning_agent.llm.invoke = Mock(return_value=mock_response)
    
    # Run test
    result = decisioning_agent.create_decision_tree("context", ["criteria"])
    assert result["success"]
```

### Test Organization

```python
import pytest

@pytest.mark.unit
@pytest.mark.registry
class TestAgentRegistry:
    """Test agent registry functionality"""
    
    def test_feature_one(self):
        """Test description"""
        # Arrange
        # Act
        # Assert
        pass
    
    def test_feature_two(self):
        """Test description"""
        pass
```

## Best Practices

1. **Arrange-Act-Assert Pattern**
   ```python
   def test_something():
       # Arrange - setup
       agent = ConcreteAgent()
       
       # Act - execute
       result = agent.do_something()
       
       # Assert - verify
       assert result["success"]
   ```

2. **Use Descriptive Test Names**
   ```python
   # Good
   def test_register_agent_adds_to_registry():
       pass
   
   # Bad
   def test_register():
       pass
   ```

3. **One Assertion Per Test (When Possible)**
   ```python
   # Good - focused test
   def test_agent_has_correct_id():
       agent = MyAgent("test_id", "name")
       assert agent.agent_id == "test_id"
   
   def test_agent_has_correct_name():
       agent = MyAgent("id", "test_name")
       assert agent.agent_name == "test_name"
   ```

4. **Use Fixtures for Common Setup**
   ```python
   @pytest.fixture
   def configured_agent():
       return MyAgent(config=mock_config)
   
   def test_with_fixture(configured_agent):
       result = configured_agent.execute("query")
       assert result["success"]
   ```

5. **Test Both Success and Failure Cases**
   ```python
   def test_create_decision_tree_success(agent):
       result = agent.create_decision_tree("context", ["criteria"])
       assert result["success"]
   
   def test_create_decision_tree_failure(agent):
       agent.llm.invoke = Mock(side_effect=Exception("error"))
       result = agent.create_decision_tree("context", ["criteria"])
       assert not result["success"]
   ```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements-test.txt
    pytest --cov --cov-report=xml
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

### Import Errors

If you see import errors:
```bash
# Ensure tests directory has __init__.py
touch tests/__init__.py

# Or run pytest from project root
cd /path/to/orchestration_system
pytest
```

### Fixture Not Found

Ensure `conftest.py` is in the tests directory and pytest can discover it.

### Mock Not Working

```python
# Make sure to patch at the right location
# Patch where it's used, not where it's defined
@patch('agents.decisioning_agent.AzureChatOpenAI')
def test_something(mock_llm):
    pass
```

## Future Test Additions

Consider adding tests for:
- [ ] Workflow execution logic
- [ ] Error recovery mechanisms
- [ ] Rate limiting behavior
- [ ] Concurrent request handling
- [ ] Agent performance metrics
- [ ] Integration tests with test doubles

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

## Questions?

For questions about the test suite:
1. Check this README
2. Review test examples in test files
3. Check pytest documentation