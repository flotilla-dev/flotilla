# config/loader.py

import os
from typing import Dict, Any, Optional

from azure.identity import DefaultAzureCredential
from azure.appconfiguration import AzureAppConfigurationClient
from azure.keyvault.secrets import SecretClient
from dotenv import dotenv_values

from config.application_settings import ApplicationSettings
from config.flotilla_setttings import FlotillaSettings
from .settings import Settings


class ConfigLoader:
    """
    Loads configuration from:
      - OS environment variables
      - Environment-specific .env files
      - Azure App Configuration
      - Azure Key Vault secret references
    """

    # ------------------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------------------

    @staticmethod
    def load(env: Optional[str] = None) -> Settings:
        """
        Main entry point for building a Settings instance with fully resolved config.

        env: "LOCAL", "DEV", "UAT", "PROD"
        """

        # Determine environment (LOCAL -> default)
        environment = env or os.getenv("APP_ENV", "LOCAL").upper()

        # 1. Load environment-specific .env overrides
        env_values = ConfigLoader._load_env_file(environment)

        # 2. Load Azure App Configuration values
        app_config_values = ConfigLoader._load_app_configuration_if_enabled()

        # 3. Combine .env + Azure AppConfiguration + OS env vars
        merged = ConfigLoader._merge_sources(
            file_env=env_values,
            app_config=app_config_values,
            os_env=os.environ,
        )

        # 4. Resolve KeyVault references inside all merged values
        resolved = ConfigLoader._resolve_keyvault_references(merged)

        # 5. Filter for only Frmaeowrk keys
        framework_keys = set(FlotillaSettings.model_fields.keys())

        # framework_values = only keys that match FrameworkSettings fields
        framework_values = {k: v for k, v in resolved.items() if k in framework_keys}

        # application_values = everything else 
        application_values = {k: v for k, v in resolved.items() if k not in framework_keys}

        # 6. Finally construct the Settings object using resolved values
        return Settings(
            flotilla=FlotillaSettings(**framework_values),
            application=ApplicationSettings(**application_values),
        )    


    # ------------------------------------------------------------------------------
    # ENV FILE LOADING
    # ------------------------------------------------------------------------------

    @staticmethod
    def _load_env_file(environment: str) -> Dict[str, Any]:
        """
        Loads .env files for specific environments:
         .env.local, .env.dev, .env.uat, .env.prod
        """

        filename = f".env.{environment.lower()}"
        if not os.path.exists(filename):
            print(f"ConfigLoader: No {filename} file found. Skipping.")
            return {}

        print(f"ConfigLoader: Loading {filename}")
        return dotenv_values(filename)

    # ------------------------------------------------------------------------------
    # AZURE APP CONFIGURATION
    # ------------------------------------------------------------------------------

    @staticmethod
    def _load_app_configuration_if_enabled() -> Dict[str, Any]:
        """
        Loads key-values from Azure App Configuration if configured.
        Requires the environment variable:
          AZURE_APP_CONFIG_ENDPOINT=https://xxx.azconfig.io
        """

        endpoint = os.getenv("AZURE_APP_CONFIG_ENDPOINT")
        if not endpoint:
            return {}

        print(f"ConfigLoader: Connecting to Azure App Configuration at {endpoint}...")

        try:
            credential = DefaultAzureCredential()
            client = AzureAppConfigurationClient(endpoint, credential)

            settings_dict = {}

            for setting in client.list_configuration_settings():
                # Key Vault-stored strings usually appear as: 
                # {"value": "@Microsoft.KeyVault(SecretUri=...)"}
                settings_dict[setting.key] = setting.value

            print(f"ConfigLoader: Loaded {len(settings_dict)} values from App Configuration.")
            return settings_dict

        except Exception as ex:
            print(f"ConfigLoader: Failed to load Azure App Configuration: {ex}")
            return {}


    @staticmethod
    def _filter_to_settings_fields(values: Dict[str, Any]) -> Dict[str, Any]:
        """Return only keys that exist as fields on the Settings model."""
        allowed = set(Settings.model_fields.keys())
        return {k: v for k, v in values.items() if k in allowed}

    # ------------------------------------------------------------------------------
    # KEY VAULT RESOLUTION
    # ------------------------------------------------------------------------------

    @staticmethod
    def _resolve_keyvault_references(values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolves references like:
          "@Microsoft.KeyVault(SecretUri=https://myvault.vault.azure.net/secrets/my-secret)"
        """

        resolved = {}
        for key, value in values.items():
            if isinstance(value, str) and value.startswith("@Microsoft.KeyVault("):
                secret_value = ConfigLoader._fetch_keyvault_secret(value)
                resolved[key] = secret_value
            else:
                resolved[key] = value

        return resolved

    @staticmethod
    def _fetch_keyvault_secret(value: str) -> Optional[str]:
        """
        Extract SecretUri from the KeyVault reference and fetch the actual secret.
        """

        try:
            # Example format:
            # @Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/<secret-name>/version)
            prefix = "SecretUri="
            start = value.find(prefix) + len(prefix)
            end = value.find(")", start)
            secret_uri = value[start:end]

            credential = DefaultAzureCredential()
            client = SecretClient(
                vault_url=secret_uri.split("/secrets/")[0],
                credential=credential
            )

            secret_name = secret_uri.split("/secrets/")[1].split("/")[0]
            secret = client.get_secret(secret_name)

            print(f"ConfigLoader: Resolved KeyVault secret for {secret_name}")
            return secret.value

        except Exception as ex:
            print(f"ConfigLoader: Failed to resolve KeyVault reference: {ex}")
            return None

    # ------------------------------------------------------------------------------
    # MERGING LOGIC
    # ------------------------------------------------------------------------------

    @staticmethod
    def _merge_sources(
        file_env: Dict[str, Any],
        app_config: Dict[str, Any],
        os_env: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merges configuration sources in precedence order:
          1. OS environment variables
          2. Azure App Configuration
          3. .env.<env> file
        """

        merged = {}

        # 3rd priority → environment-specific .env
        merged.update(file_env)

        # 2nd priority → Azure App Configuration
        merged.update(app_config)

        # 1st priority → OS Environment Variables (highest)
        merged.update(os_env)

        return merged
