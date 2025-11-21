import os
import yaml
from typing import Dict, Any, Optional

from azure.identity import DefaultAzureCredential
from azure.appconfiguration import AzureAppConfigurationClient
from azure.keyvault.secrets import SecretClient
from dotenv import dotenv_values

from config.application_settings import ApplicationSettings
from config.flotilla_setttings import FlotillaSettings
from config.settings import Settings


class ConfigLoader:
    """
    Enhanced configuration loader with hierarchical YAML support.

    Supports:
      - Nested flotilla.yml, agents.yml, tools.yml, feature_flags.yml
      - Environment override files: *.local.yml, *.dev.yml, *.uat.yml, *.prod.yml
      - .env.* files
      - OS environment variables
      - Azure App Configuration
      - KeyVault secret resolution
      - Per-agent inheritance from flotilla defaults
    """

    # ----------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------
    @staticmethod
    def load(env: Optional[str] = None, config_dir: str = "./config") -> Settings:

        environment = env or os.getenv("APP_ENV", "LOCAL").upper()

        # ------------------------------------------------------------------
        # Load hierarchical YAML (base + override)
        # ------------------------------------------------------------------
        flotilla_yaml = ConfigLoader._load_yaml_pair(
            f"{config_dir}/flotilla.yml",
            f"{config_dir}/flotilla.{environment.lower()}.yml",
        )

        agents_yaml = ConfigLoader._load_yaml_pair(
            f"{config_dir}/agents.yml",
            f"{config_dir}/agents.{environment.lower()}.yml",
        )

        tools_yaml = ConfigLoader._load_yaml_pair(
            f"{config_dir}/tools.yml",
            f"{config_dir}/tools.{environment.lower()}.yml",
        )

        feature_flags_yaml = ConfigLoader._load_yaml_pair(
            f"{config_dir}/feature_flags.yml",
            f"{config_dir}/feature_flags.{environment.lower()}.yml",
        )

        # ------------------------------------------------------------------
        # Traditional sources (.env, Azure AppConfig, OS env)
        # ------------------------------------------------------------------
        env_values = ConfigLoader._load_env_file(environment)
        app_config_values = ConfigLoader._load_app_configuration_if_enabled()

        scalar_merged = ConfigLoader._merge_scalar_sources(
            file_env=env_values,
            app_config=app_config_values,
            os_env=os.environ,
        )

        scalar_resolved = ConfigLoader._resolve_keyvault_references(scalar_merged)

        # ------------------------------------------------------------------
        # Apply hierarchical YAML to FlotillaSettings (flattened)
        # ------------------------------------------------------------------
        flat_flotilla = ConfigLoader._flatten_yaml(flotilla_yaml)

        flotilla_settings = FlotillaSettings(
            **ConfigLoader._extract_settings_fields(flat_flotilla, scalar_resolved)
        )

        # ------------------------------------------------------------------
        # Application settings (agents, tools, feature flags)
        # ------------------------------------------------------------------
        agent_configs = ConfigLoader._apply_agent_overrides(
            agents_yaml=agents_yaml,
            flotilla_defaults=flotilla_settings,
        )

        application_settings = ApplicationSettings(
            agent_configs=agent_configs,
            tool_configs=tools_yaml,
            feature_flags=feature_flags_yaml,
        )

        return Settings(
            flotilla=flotilla_settings,
            application=application_settings,
        )

    # ==========================================================================
    # YAML LOADING + MERGING
    # ==========================================================================
    @staticmethod
    def _load_yaml(path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> Dict:
        result = dict(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _load_yaml_pair(base_path: str, override_path: str) -> Dict[str, Any]:
        base_yaml = ConfigLoader._load_yaml(base_path)
        override_yaml = ConfigLoader._load_yaml(override_path)
        return ConfigLoader._deep_merge(base_yaml, override_yaml)

    # ==========================================================================
    # YAML FLATTENING (hierarchical → LLM__API_KEY style)
    # ==========================================================================
    @staticmethod
    def _flatten_yaml(d: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}__{k}" if parent_key else k
            new_key = new_key.upper()  # Match Pydantic fields
            if isinstance(v, dict):
                items.update(ConfigLoader._flatten_yaml(v, new_key))
            else:
                items[new_key] = v
        return items

    # ==========================================================================
    # ENV FILES + APP CONFIG
    # ==========================================================================
    @staticmethod
    def _load_env_file(environment: str) -> Dict[str, Any]:
        filename = f".env.{environment.lower()}"
        return dotenv_values(filename) if os.path.exists(filename) else {}

    @staticmethod
    def _load_app_configuration_if_enabled() -> Dict[str, Any]:
        endpoint = os.getenv("AZURE_APP_CONFIG_ENDPOINT")
        if not endpoint:
            return {}

        try:
            credential = DefaultAzureCredential()
            client = AzureAppConfigurationClient(endpoint, credential)
            return {item.key: item.value for item in client.list_configuration_settings()}
        except Exception:
            return {}

    @staticmethod
    def _merge_scalar_sources(file_env: Dict, app_config: Dict, os_env: Dict) -> Dict:
        merged = {}
        merged.update(file_env)
        merged.update(app_config)
        merged.update(os_env)
        return merged

    # ==========================================================================
    # KEY VAULT
    # ==========================================================================
    @staticmethod
    def _resolve_keyvault_references(values: Dict[str, Any]) -> Dict[str, Any]:
        resolved = {}
        for k, v in values.items():
            if isinstance(v, str) and v.startswith("@Microsoft.KeyVault("):
                resolved[k] = ConfigLoader._fetch_keyvault_secret(v)
            else:
                resolved[k] = v
        return resolved

    @staticmethod
    def _fetch_keyvault_secret(value: str) -> Optional[str]:
        try:
            prefix = "SecretUri="
            start = value.find(prefix) + len(prefix)
            end = value.find(")", start)
            uri = value[start:end]
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=uri.split("/secrets/")[0], credential=credential)
            secret_name = uri.split("/secrets/")[1].split("/")[0]
            return client.get_secret(secret_name).value
        except Exception:
            return None

    # ==========================================================================
    # MAPPING YAML → Pydantic Settings Fields
    # ==========================================================================
    @staticmethod
    def _extract_settings_fields(flat_yaml: Dict[str, Any], scalar_overrides: Dict[str, Any]) -> Dict[str, Any]:
        allowed = set(FlotillaSettings.model_fields.keys())
        final = {}

        # YAML first
        for key, value in flat_yaml.items():
            if key in allowed:
                final[key] = value

        # Scalar overrides take precedence
        for key, value in scalar_overrides.items():
            key_upper = key.upper()
            if key_upper in allowed:
                final[key_upper] = value

        return final

    # ==========================================================================
    # AGENT OVERRIDE LOGIC (inherit flotilla defaults)
    # ==========================================================================
    @staticmethod
    def _apply_agent_overrides(agents_yaml: Dict[str, Any], flotilla_defaults: FlotillaSettings) -> Dict[str, Any]:

        final = {}
        for agent_name, agent_cfg in agents_yaml.items():

            base_llm = {
                "temperature": float(flotilla_defaults.LLM__TEMPERATURE),
                "model": flotilla_defaults.LLM__MODEL,
                "type": flotilla_defaults.LLM__TYPE,
            }

            merged = {"llm": base_llm}
            merged = ConfigLoader._deep_merge(merged, agent_cfg)

            final[agent_name] = merged

        return final
