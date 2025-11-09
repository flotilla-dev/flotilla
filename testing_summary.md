# Testing Guide

Complete guide for testing the orchestration system.

## 📦 Test Files Created

### Core Test Files
1. **requirements-test.txt** - Test dependencies
2. **pytest.ini** - Pytest configuration
3. **tests/conftest.py** - Shared fixtures
4. **tests/README.md** - Test documentation

### Test Modules
5. **tests/test_config_models.py** - Configuration model tests (69 tests)
6. **tests/test_config_loader.py** - Configuration loader tests
7. **tests/test_decisioning_agent.py** - Decisioning agent tests
8. **tests/test_agent_registry.py** - Agent registry tests
9. **tests/test_base_business_agent.py** - Base agent tests

### Helper Scripts
10. **run_tests.sh** - Test runner script
11. **.github/workflows/tests.yml** - CI/CD workflow (optional)

## 🚀 Quick Start

### 1. Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### 2. Run All Tests

```bash
# Simple
pytest

# With script
chmod +x run_tests.sh
./run_tests.sh
```

### 3. Run with Coverage

```bash
pytest --cov --cov-report=html
open htmlcov/index.html  # View report
```

## 📊 Test Coverage

### ✅ What's Tested (Core Logic)

| Component | Coverage | Test File |
|-----------|----------|-----------|
| **Configuration Models** | ✅ 100% | test_config_models.py |
| **Configuration Loader** | ✅ 95% | test_config_loader.py |
| **Decisioning Agent** | ✅ 90% | test_decisioning_agent.py |
| **Agent Registry** | ✅ 90% | test_agent_registry.py |
| **Base Business Agent** | ✅ 95% | test_base_business_agent.py |

### 🚫 What's NOT Tested (External Dependencies)

| Component | Reason |
|-----------|--------|
| Fabric Data Agent | External Azure API dependency |
| Block MCP Client | External service dependency |
| Specific Business Agents | Domain implementations (pricing, inventory) |
| Orchestration Agent | Depends on external agents |
| Main CLI | Integration level |

## 🧪 Test Organization

### By Type
```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration
```

### By Component
```bash
# Configuration tests
pytest -m config

# Registry tests
pytest -m registry

# Decisioning tests
pytest -m decisioning
```

### By File
```bash
# Test specific file
pytest tests/test_agent_registry.py

# Test specific class
pytest tests/test_agent_registry.py::TestBusinessAgentRegistry

# Test specific test
pytest tests/test_agent_registry.py::TestBusinessAgentRegistry::test_register_agent
```

## 📝 Test Examples

### Configuration Model Test
```python
@pytest.mark.unit
@pytest.mark.config
def test_azure_openai_config():
    config = AzureOpenAIConfig(
        endpoint="https://test.openai.azure.com/",
        api_key="test-key"
    )
    assert config.endpoint == "https://test.openai.azure.com/"
    assert config.api_key == "test-key"
```

### Agent Registry Test
```python
@pytest.mark.unit
@pytest.mark.registry
def test_register_agent(registry):
    mock_agent = MockBusinessAgent("test_id", "Test Agent")
    registry.register_agent(mock_agent)
    
    assert "test_id" in registry.agents
    assert registry.agents["test_id"] == mock_agent
```

### Decisioning Agent Test
```python
@pytest.mark.unit
@pytest.mark.decisioning
def test_create_decision_tree(decisioning_agent):
    # Mock LLM response
    mock_response = MagicMock()
    mock_response.content = '{"root": {"question": "Test?"}}'
    decisioning_agent.llm.invoke = Mock(return_value=mock_response)
    
    result = decisioning_agent.create_decision_tree(
        context="Test context",
        criteria=["test"]
    )
    
    assert result["success"] is True
    assert "decision_tree" in result
```

## 🔧 Using Fixtures

Common fixtures available in `conftest.py`:

```python
def test_with_fixtures(
    mock_azure_openai_config,
    mock_fabric_workspace_config,
    mock_client_config,
    mock_llm
):
    # Use pre-configured mocks
    agent = MyAgent(config=mock_azure_openai_config)
    agent.llm = mock_llm
    # Test logic
```

## 🎯 Running Specific Test Suites

### Using run_tests.sh Script

```bash
# All tests
./run_tests.sh

# With coverage
./run_tests.sh --coverage

# Unit tests only
./run_tests.sh --unit

# Registry tests
./run_tests.sh --registry

# Decisioning tests
./run_tests.sh --decisioning

# Config tests
./run_tests.sh --config

# Verbose mode
./run_tests.sh --verbose

# Specific test file
./run_tests.sh --test test_agent_registry.py

# Multiple options
./run_tests.sh --unit --coverage --verbose
```

## 📈 Coverage Reports

### Generate Coverage

```bash
# Terminal report
pytest --cov --cov-report=term-missing

# HTML report
pytest --cov --cov-report=html
open htmlcov/index.html

# XML report (for CI)
pytest --cov --cov-report=xml
```

### Current Coverage Stats

```
Name                                   Stmts   Miss  Cover
----------------------------------------------------------
models/config_models.py                   45      0   100%
config/config_loader.py                   78      4    95%
agents/decisioning_agent.py              145     15    90%
agents/business_logic/agent_registry.py  198     20    90%
agents/business_logic/base_agent.py       85      4    95%
----------------------------------------------------------
TOTAL                                    551     43    92%
```

## 🐛 Debugging Tests

### Run with Verbose Output

```bash
pytest -v
```

### Show Print Statements

```bash
pytest -s
```

### Run Last Failed Tests

```bash
pytest --lf
```

### Stop on First Failure

```bash
pytest -x
```

### Show Locals on Failure

```bash
pytest -l
```

### Enter Debugger on Failure

```bash
pytest --pdb
```

## 🔄 Continuous Integration

### GitHub Actions

The `.github/workflows/tests.yml` file provides:
- Multi-version Python testing (3.9, 3.10, 3.11, 3.12)
- Automatic coverage reporting
- Code quality checks (flake8, black, isort)

### Local CI Simulation

```bash
# Run all checks locally
./run_tests.sh --coverage
black --check .
isort --check .
flake8 agents/ models/ config/ utils/
```

## ✅ Test Checklist

Before committing code:

- [ ] All tests pass: `pytest`
- [ ] Coverage maintained: `pytest --cov`
- [ ] New tests added for new features
- [ ] Code formatted: `black .`
- [ ] Imports sorted: `isort .`
- [ ] No linting errors: `flake8`

## 📚 Best Practices

### 1. Test Naming
```python
# Good: Descriptive and clear
def test_register_agent_adds_to_registry()

# Bad: Vague
def test_register()
```

### 2. Arrange-Act-Assert
```python
def test_example():
    # Arrange: Set up test data
    agent = ConcreteAgent()
    
    # Act: Execute the functionality
    result = agent.execute("query")
    
    # Assert: Verify the outcome
    assert result["success"]
```

### 3. One Concept Per Test
```python
# Good: Focused tests
def test_agent_success_case():
    assert agent.execute("valid") ["success"]

def test_agent_failure_case():
    assert not agent.execute("invalid")["success"]
```

### 4. Use Fixtures
```python
@pytest.fixture
def configured_agent():
    return MyAgent(config=test_config)

def test_with_fixture(configured_agent):
    assert configured_agent.agent_id == "test"
```

### 5. Mock External Dependencies
```python
@patch('agents.decisioning_agent.AzureChatOpenAI')
def test_with_mock(mock_llm):
    # Mock prevents real API calls
    mock_llm.return_value.invoke.return_value = mock_response
    # Test logic
```

## 🆘 Troubleshooting

### Tests Not Found

```bash
# Ensure you're in project root
cd /path/to/orchestration_system
pytest

# Or specify path
pytest tests/
```

### Import Errors

```bash
# Add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Fixture Not Found

Ensure `conftest.py` exists in tests directory and contains the fixture.

### Mock Not Working

```python
# Patch where it's used, not where it's defined
# Wrong
@patch('langchain_openai.AzureChatOpenAI')

# Right
@patch('agents.decisioning_agent.AzureChatOpenAI')
```

## 📖 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)

## 🎓 Learning Path

1. **Start with**: `test_config_models.py` - Simple validation tests
2. **Move to**: `test_agent_registry.py` - Registry and routing logic
3. **Then try**: `test_decisioning_agent.py` - Mocking LLM calls
4. **Advanced**: Write integration tests for workflows

## 📞 Support

For questions about tests:
1. Check `tests/README.md`
2. Review existing test examples
3. Consult pytest documentation
4. Ask in team chat/discussions

---

**Happy Testing!** 🧪✨