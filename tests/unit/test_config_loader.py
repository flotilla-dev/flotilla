import os
import pytest
from unittest.mock import patch, MagicMock

from config.config_loader import ConfigLoader
from config.settings import Settings


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

def test_merge_sources():
    file_env = {"A": "file", "B": "file"}
    app_config = {"B": "app", "C": "app"}
    os_env = {"C": "os", "D": "os"}

    merged = ConfigLoader._merge_sources(file_env, app_config, os_env)
    assert merged == {
        "A": "file",
        "B": "app",
        "C": "os",
        "D": "os",
    }


# --------------------------------------------------------------------------
# Test: Full ConfigLoader flow (mocking everything)
# --------------------------------------------------------------------------

@patch.object(ConfigLoader, "_load_env_file", return_value={"LOG__LEVEL": "from_env_file"})
@patch.object(ConfigLoader, "_load_app_configuration_if_enabled", return_value={"LOG__LEVEL": "from_app_config"})
@patch.object(ConfigLoader, "_resolve_keyvault_references", side_effect=lambda x: x)
def test_full_load(mock_kv, mock_app_config, mock_env_file):
    """
    Tests the full ConfigLoader.load() flow, ensuring correct merge precedence:
      OS environment > Azure AppConfig > .env file > defaults
    """

    # Inject OS-level override (highest priority)
    os.environ["LOG__LEVEL"] = "from_os"

    # Load settings through the loader
    settings = ConfigLoader.load("LOCAL")

    # Validate the override precedence:
    # OS env ("from_os") > App Config ("from_app_config") > .env ("from_env_file") > default ("INFO")
    assert settings.flotilla.LOG__LEVEL == "from_os"

    # cleanup for test isolation
    del os.environ["LOG__LEVEL"]
