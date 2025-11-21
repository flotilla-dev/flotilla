import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest
import yaml

from config.config_loader import ConfigLoader
from config.settings import Settings
from config.flotilla_setttings import FlotillaSettings



# --------------------------------------------------------------------------
# Helper: temporary .env contents
# --------------------------------------------------------------------------

@pytest.fixture
def mock_env_file(tmp_path):
    """Creates a .env.local file in a temp directory and switches CWD."""

    d = tmp_path
    env_file = d / ".env.local"
    env_file.write_text("TEST_KEY=from_env_file\n")

    # switch working directory
    old_cwd = os.getcwd()
    os.chdir(d)

    yield d

    # restore working directory
    os.chdir(old_cwd)


# --------------------------------------------------------------------------
# Test: Loading from .env file
# --------------------------------------------------------------------------

def test_load_env_file(mock_env_file):
    result = ConfigLoader._load_env_file("LOCAL")
    assert result == {"TEST_KEY": "from_env_file"}


def test_load_env_file_missing():
    result = ConfigLoader._load_env_file("DEV")  # no .env.dev exists
    assert result == {}  # silently ignored


# --------------------------------------------------------------------------
# Test: Azure App Configuration Loading
# --------------------------------------------------------------------------

@patch("config.config_loader.AzureAppConfigurationClient")
@patch("config.config_loader.DefaultAzureCredential")
def test_load_app_config(mock_cred, mock_client):
    # Mock environment variable pointing to AppConfig
    os.environ["AZURE_APP_CONFIG_ENDPOINT"] = "https://fake.azconfig.io"

    # Mock App Config client behavior
    mock_instance = MagicMock()
    mock_instance.list_configuration_settings.return_value = [
        MagicMock(key="REMOTE_SETTING", value="remote_val")
    ]
    mock_client.return_value = mock_instance

    values = ConfigLoader._load_app_configuration_if_enabled()
    assert values == {"REMOTE_SETTING": "remote_val"}

    del os.environ["AZURE_APP_CONFIG_ENDPOINT"]


# --------------------------------------------------------------------------
# Test: Key Vault secret resolution
# --------------------------------------------------------------------------

@patch("config.config_loader.SecretClient")
@patch("config.config_loader.DefaultAzureCredential")
def test_key_vault_resolution(mock_cred, mock_secret_client):
    # Mock KeyVault secret client
    fake_secret_client = MagicMock()
    fake_secret = MagicMock(value="resolved_secret")
    fake_secret_client.get_secret.return_value = fake_secret

    # Patch SecretClient() to return our fake client
    mock_secret_client.return_value = fake_secret_client

    # reference-style Azure KV value
    kv_ref = "@Microsoft.KeyVault(SecretUri=https://vault.vault.azure.net/secrets/my-key/abcd)"

    resolved = ConfigLoader._resolve_keyvault_references({"API_KEY": kv_ref})
    assert resolved["API_KEY"] == "resolved_secret"


def test_key_vault_resolution_no_reference():
    resolved = ConfigLoader._resolve_keyvault_references({"KEY": "normal_value"})
    assert resolved["KEY"] == "normal_value"


# --------------------------------------------------------------------------
# Test: Merging logic
# --------------------------------------------------------------------------

def test_merge_scalar_sources():
    file_env = {"A": "file", "B": "file"}
    app_config = {"B": "app", "C": "app"}
    os_env = {"C": "os", "D": "os"}

    merged = ConfigLoader._merge_scalar_sources(
        file_env=file_env,
        app_config=app_config,
        os_env=os_env
    )

    assert merged == {
        "A": "file",   # from file_env
        "B": "app",    # app_config overrides file
        "C": "os",     # os_env overrides app_config
        "D": "os",     # from os_env
    }

# --------------------------------------------------------------------------
# Test: Full ConfigLoader flow (mocking everything)
# --------------------------------------------------------------------------

@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory with base YAML files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create base config files
        base_configs = {
            "flotilla.yml": {
                "llm": {
                    "type": "openai",
                    "model": "gpt-4",
                    "temperature": "0.7",  # String for pydantic
                    "api_key": "default_key"
                },
                "log": {"level": "INFO"},
                "tool_registry": {
                    "packages": ["package1", "package2"]
                },
                "agent_registry": {
                    "packages": ["agent_package1"]
                }
            },
            "agents.yml": {
                "agent_default": {
                    "llm": {"temperature": "0.5"}
                }
            },
            "tools.yml": {
                "tool_1": {"enabled": True}
            },
            "feature_flags.yml": {
                "experimental": False
            }
        }
        
        for filename, content in base_configs.items():
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, "w") as f:
                yaml.dump(content, f)
        
        yield tmpdir


def test_full_load_with_override_precedence(temp_config_dir):
    """
    Tests the full ConfigLoader.load() flow with proper precedence:
      OS environment > Azure AppConfig > .env file > YAML defaults
    """
    
    with patch.object(ConfigLoader, "_load_env_file", return_value={"LOG__LEVEL": "from_env_file"}), \
         patch.object(ConfigLoader, "_load_app_configuration_if_enabled", return_value={"LOG__LEVEL": "from_app_config"}), \
         patch.object(ConfigLoader, "_resolve_keyvault_references", side_effect=lambda x: x):
        
        # Inject OS-level override (highest priority)
        os.environ["LOG__LEVEL"] = "from_os"
        
        try:
            settings = ConfigLoader.load("LOCAL", config_dir=temp_config_dir)
            
            # Validate the override precedence:
            # OS env ("from_os") > App Config ("from_app_config") > .env ("from_env_file")
            assert settings.flotilla.LOG__LEVEL == "from_os"
            
            # Verify the settings object is properly constructed
            assert isinstance(settings, Settings)
            assert isinstance(settings.flotilla, FlotillaSettings)
            assert settings.application is not None
            
        finally:
            # Cleanup for test isolation
            if "LOG__LEVEL" in os.environ:
                del os.environ["LOG__LEVEL"]


@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory with base YAML files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create base config files matching FlotillaSettings field types
        base_configs = {
            "flotilla.yml": {
                "llm": {
                    "type": "openai",
                    "model": "gpt-4",
                    "temperature": "0.7",  # String for pydantic
                    "api_key": "default_key"
                },
                "log": {"level": "INFO"},
                "tool_registry": {
                    "packages": ["package1", "package2"]
                },
                "agent_registry": {
                    "packages": ["agent_package1"]
                }
            },
            "agents.yml": {
                "agent_default": {
                    "llm": {"temperature": "0.5"}
                }
            },
            "tools.yml": {
                "tool_1": {"enabled": True}
            },
            "feature_flags.yml": {
                "experimental": False
            }
        }
        
        for filename, content in base_configs.items():
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, "w") as f:
                yaml.dump(content, f)
        
        yield tmpdir


def test_full_load_with_override_precedence(temp_config_dir):
    """
    Tests the full ConfigLoader.load() flow with proper precedence:
      OS environment > Azure AppConfig > .env file > YAML defaults
    """
    
    with patch.object(ConfigLoader, "_load_env_file", return_value={"LOG__LEVEL": "from_env_file"}), \
         patch.object(ConfigLoader, "_load_app_configuration_if_enabled", return_value={"LOG__LEVEL": "from_app_config"}), \
         patch.object(ConfigLoader, "_resolve_keyvault_references", side_effect=lambda x: x):
        
        # Inject OS-level override (highest priority)
        os.environ["LOG__LEVEL"] = "from_os"
        
        try:
            settings = ConfigLoader.load("LOCAL", config_dir=temp_config_dir)
            
            # Validate the override precedence:
            # OS env ("from_os") > App Config ("from_app_config") > .env ("from_env_file")
            assert settings.flotilla.LOG__LEVEL == "from_os"
            
            # Verify the settings object is properly constructed
            assert isinstance(settings, Settings)
            assert isinstance(settings.flotilla, FlotillaSettings)
            assert settings.application is not None
            
        finally:
            # Cleanup for test isolation
            if "LOG__LEVEL" in os.environ:
                del os.environ["LOG__LEVEL"]


def test_load_yaml_pair_with_environment_override(temp_config_dir):
    """
    Tests hierarchical YAML loading: base + environment-specific override.
    """
    
    # Create environment-specific override
    env_override = {
        "llm": {
            "temperature": 0.9,
            "api_key": "env_specific_key"
        },
        "log": {"level": "DEBUG"}
    }
    
    override_path = os.path.join(temp_config_dir, "flotilla.local.yml")
    with open(override_path, "w") as f:
        yaml.dump(env_override, f)
    
    result = ConfigLoader._load_yaml_pair(
        os.path.join(temp_config_dir, "flotilla.yml"),
        override_path
    )
    
    # Base values preserved where not overridden
    assert result["llm"]["model"] == "gpt-4"
    # Override values take precedence
    assert result["llm"]["temperature"] == 0.9
    assert result["llm"]["api_key"] == "env_specific_key"
    assert result["log"]["level"] == "DEBUG"


def test_flatten_yaml_hierarchical_structure():
    """
    Tests flattening of nested YAML into double-underscore format.
    """
    
    nested = {
        "llm": {
            "type": "openai",
            "api": {
                "key": "secret",
                "endpoint": "https://api.openai.com"
            }
        },
        "log": {
            "level": "INFO"
        }
    }
    
    flattened = ConfigLoader._flatten_yaml(nested)
    
    assert flattened["LLM__TYPE"] == "openai"
    assert flattened["LLM__API__KEY"] == "secret"
    assert flattened["LLM__API__ENDPOINT"] == "https://api.openai.com"
    assert flattened["LOG__LEVEL"] == "INFO"


def test_merge_scalar_sources_precedence():
    """
    Tests that scalar source merging respects precedence:
    OS environment > App Config > .env file
    """
    
    file_env = {"KEY_A": "from_file", "KEY_B": "from_file"}
    app_config = {"KEY_A": "from_app_config", "KEY_C": "from_app_config"}
    os_env = {"KEY_A": "from_os"}
    
    merged = ConfigLoader._merge_scalar_sources(file_env, app_config, os_env)
    
    # OS env wins
    assert merged["KEY_A"] == "from_os"
    # App config wins over file
    assert merged["KEY_C"] == "from_app_config"
    # File values still present
    assert merged["KEY_B"] == "from_file"


def test_extract_settings_fields_with_overrides(temp_config_dir):
    """
    Tests extraction of allowed FlotillaSettings fields with precedence.
    """
    
    flat_yaml = {
        "LLM__MODEL": "gpt-3.5-turbo",
        "LLM__TEMPERATURE": 0.5,
        "INVALID_FIELD": "should_be_ignored"
    }
    
    scalar_overrides = {
        "llm__temperature": 0.9  # Override from env
    }
    
    result = ConfigLoader._extract_settings_fields(flat_yaml, scalar_overrides)
    
    assert result["LLM__MODEL"] == "gpt-3.5-turbo"
    assert result["LLM__TEMPERATURE"] == 0.9  # Scalar override takes precedence
    assert "INVALID_FIELD" not in result


def test_apply_agent_overrides_inherits_flotilla_defaults(temp_config_dir):
    """
    Tests that per-agent configs inherit and can override flotilla defaults.
    """
    
    # Create mock flotilla settings
    mock_flotilla = MagicMock(spec=FlotillaSettings)
    mock_flotilla.LLM__TYPE = "openai"
    mock_flotilla.LLM__MODEL = "gpt-4"
    mock_flotilla.LLM__TEMPERATURE = 0.7
    
    agents_yaml = {
        "agent_a": {
            "llm": {"temperature": 0.5}  # Override temperature
        },
        "agent_b": {
            "tools": ["tool_1", "tool_2"]
        }
    }
    
    result = ConfigLoader._apply_agent_overrides(agents_yaml, mock_flotilla)
    
    # Agent A inherits base LLM config but overrides temperature
    assert result["agent_a"]["llm"]["type"] == "openai"
    assert result["agent_a"]["llm"]["model"] == "gpt-4"
    assert result["agent_a"]["llm"]["temperature"] == 0.5
    
    # Agent B inherits base LLM config and adds tools
    assert result["agent_b"]["llm"]["type"] == "openai"
    assert result["agent_b"]["llm"]["temperature"] == 0.7 # test default is copied from parent
    assert result["agent_b"]["tools"] == ["tool_1", "tool_2"]


def test_resolve_keyvault_references():
    """
    Tests KeyVault secret reference resolution.
    """
    
    mock_secret_client = MagicMock()
    mock_secret_client.get_secret.return_value.value = "resolved_secret_value"
    
    with patch("config.config_loader.SecretClient", return_value=mock_secret_client), \
         patch("config.config_loader.DefaultAzureCredential"):
        
        keyvault_ref = "@Microsoft.KeyVault(SecretUri=https://myvault.vault.azure.net/secrets/db-password/abc123)"
        result = ConfigLoader._fetch_keyvault_secret(keyvault_ref)
        
        assert result == "resolved_secret_value"
        mock_secret_client.get_secret.assert_called_once()


def test_load_with_missing_yaml_files(temp_config_dir):
    """
    Tests that loader handles missing YAML files gracefully.
    """
    
    # Remove one of the expected files
    os.remove(os.path.join(temp_config_dir, "agents.yml"))
    
    with patch.object(ConfigLoader, "_load_env_file", return_value={}), \
         patch.object(ConfigLoader, "_load_app_configuration_if_enabled", return_value={}), \
         patch.object(ConfigLoader, "_resolve_keyvault_references", side_effect=lambda x: x):
        
        # Should not raise, should handle gracefully with empty dict
        settings = ConfigLoader.load("LOCAL", config_dir=temp_config_dir)
        
        assert isinstance(settings, Settings)
        assert settings.application.agent_configs == {}