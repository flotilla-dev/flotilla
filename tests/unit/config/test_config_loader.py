import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest
import yaml

from config.config_loader import ConfigLoader
from config.config_factory import ConfigFactory
from config.settings import Settings
from config.flotilla_setttings import FlotillaSettings


# ================================================================
# FIXTURES
# ================================================================

@pytest.fixture
def mock_env_file(tmp_path):
    """Creates .env.local and switches CWD temporarily."""
    env_file = tmp_path / ".env.local"
    env_file.write_text("TEST_KEY=from_env_file\n")

    old = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(old)


@pytest.fixture
def temp_config_dir():
    """Base YAML configs for full load tests."""
    with tempfile.TemporaryDirectory() as tmp:
        base = {
            "flotilla.yml": {
                "llm": {"type": "openai", "model": "gpt-4", "temperature": 0.7, "api_key": "default_key"},
                "log": {"level": "INFO"},
                "tool_registry": {"packages": ["package1", "package2"]},
                "agent_registry": {"packages": ["agent_package1"]}
            },
            "agents.yml": {"agent_default": {"llm": {"temperature": 0.5}}},
            "tools.yml": {"tool_1": {"enabled": True}},
            "feature_flags.yml": {"experimental": False},
        }

        for file, content in base.items():
            with open(os.path.join(tmp, file), "w") as f:
                yaml.dump(content, f)

        yield tmp


# ================================================================
# ENV FILE LOADING
# ================================================================

def test_load_env_file(mock_env_file):
    assert ConfigLoader._load_env_file("LOCAL") == {"TEST_KEY": "from_env_file"}


def test_load_env_missing_no_error():
    assert ConfigLoader._load_env_file("DEV") == {}  # silent no-op


# ================================================================
# AZURE APP CONFIG & KEYVAULT
# ================================================================

@patch("config.config_loader.AzureAppConfigurationClient")
@patch("config.config_loader.DefaultAzureCredential")
def test_load_app_config(mock_cred, mock_client):
    os.environ["AZURE_APP_CONFIG_ENDPOINT"] = "https://fake.azconfig.io"

    mock_instance = MagicMock()
    mock_instance.list_configuration_settings.return_value = [MagicMock(key="REMOTE_SETTING", value="remote_val")]
    mock_client.return_value = mock_instance

    assert ConfigLoader._load_app_configuration_if_enabled() == {"REMOTE_SETTING": "remote_val"}
    del os.environ["AZURE_APP_CONFIG_ENDPOINT"]


@patch("config.config_loader.SecretClient")
@patch("config.config_loader.DefaultAzureCredential")
def test_keyvault_resolution(mock_cred, mock_secret_client):
    fake = MagicMock()
    fake.get_secret.return_value.value = "resolved"
    mock_secret_client.return_value = fake

    ref = "@Microsoft.KeyVault(SecretUri=https://vault/secrets/key/x)"
    assert ConfigLoader._resolve_keyvault_references({"API": ref})["API"] == "resolved"


def test_keyvault_passthrough_normal():
    assert ConfigLoader._resolve_keyvault_references({"X": "plain"})["X"] == "plain"


# ================================================================
# MERGING + SCALAR PRECEDENCE
# ================================================================

def test_merge_scalar_precedence():
    out = ConfigLoader._merge_scalar_sources(
        file_env={"A": "file", "B": "file"},
        app_config={"B": "app", "C": "app"},
        os_env={"C": "os", "D": "os"},
    )
    assert out == {"A": "file", "B": "app", "C": "os", "D": "os"}


# ================================================================
# YAML LOAD / FLATTEN / OVERRIDE LOGIC
# ================================================================

def test_load_yaml_pair(temp_config_dir):
    override = {"llm": {"temperature": 0.9, "api_key": "env_key"}, "log": {"level": "DEBUG"}}
    path = os.path.join(temp_config_dir, "flotilla.local.yml")
    with open(path, "w") as f: yaml.dump(override, f)

    data = ConfigLoader._load_yaml_pair(
        os.path.join(temp_config_dir, "flotilla.yml"), path
    )

    assert data["llm"]["model"] == "gpt-4"
    assert data["llm"]["temperature"] == 0.9
    assert data["log"]["level"] == "DEBUG"


def test_yaml_flattening():
    nested = {"llm": {"api": {"key": "k", "url": "u"}}, "log": {"level": "I"}}
    flat = ConfigLoader._flatten_yaml(nested)
    assert flat == {"LLM__API__KEY": "k", "LLM__API__URL": "u", "LOG__LEVEL": "I"}


# ================================================================
# FULL LOADER FLOW (NARROWED TO ONE SOLID TEST)
# ================================================================

def test_full_load_end_to_end(temp_config_dir):
    with patch.object(ConfigLoader, "_load_env_file", return_value={"LOG__LEVEL": "env_file"}), \
         patch.object(ConfigLoader, "_load_app_configuration_if_enabled", return_value={"LOG__LEVEL": "app"}), \
         patch.object(ConfigLoader, "_resolve_keyvault_references", side_effect=lambda x: x):

        os.environ["LOG__LEVEL"] = "os"  # highest precedence

        try:
            settings = ConfigLoader.load("LOCAL", config_dir=temp_config_dir)
            assert settings.flotilla.LOG__LEVEL == "os"  # precedence holds
            assert isinstance(settings.flotilla, FlotillaSettings)
        finally:
            del os.environ["LOG__LEVEL"]


def test_loader_allows_missing_yaml(temp_config_dir):
    os.remove(os.path.join(temp_config_dir, "agents.yml"))

    with patch.object(ConfigLoader, "_load_env_file", return_value={}), \
         patch.object(ConfigLoader, "_load_app_configuration_if_enabled", return_value={}), \
         patch.object(ConfigLoader, "_resolve_keyvault_references", side_effect=lambda x: x):

        st = ConfigLoader.load("LOCAL", config_dir=temp_config_dir)
        assert isinstance(st.application.agent_configs, dict)
        assert st.application.agent_configs == {}

def test_feature_flags_loaded_from_yaml(temp_config_dir):
    """
    Ensures feature flags defined in feature_flags.yml are loaded into settings.flotilla.feature_flags.
    """

    # Patch external systems so full load only reads YAML data
    with patch.object(ConfigLoader, "_load_env_file", return_value={}), \
         patch.object(ConfigLoader, "_load_app_configuration_if_enabled", return_value={}), \
         patch.object(ConfigLoader, "_resolve_keyvault_references", side_effect=lambda x: x):

        settings = ConfigLoader.load("LOCAL", config_dir=temp_config_dir)

        # Feature flags should exist and reflect YAML values
        assert hasattr(settings.application, "feature_flags")
        assert isinstance(settings.application.feature_flags, dict)
        assert settings.application.feature_flags == {"experimental": False}
        assert not settings.application.feature_flags["experimental"]

def test_agent_override_llm(temp_config_dir):
    """
    Ensures values in the agents.yml file override base values in flotilla.yml for a specific agent
    """

    # Patch external systems so full load only reads YAML data
    with patch.object(ConfigLoader, "_load_env_file", return_value={}), \
         patch.object(ConfigLoader, "_load_app_configuration_if_enabled", return_value={}), \
         patch.object(ConfigLoader, "_resolve_keyvault_references", side_effect=lambda x: x):
        
        settings = ConfigLoader.load("LOCAL", config_dir=temp_config_dir)

        agent_1_config = ConfigFactory.create_business_agent_config(agent_id="agent_default", settings=settings)
        assert agent_1_config
        assert agent_1_config.llm_config.temperature == 0.5

        agent_2_config = ConfigFactory.create_business_agent_config(agent_id="test_agent", settings=settings)
        assert agent_2_config
        assert agent_2_config.llm_config.temperature == 0.7

        

