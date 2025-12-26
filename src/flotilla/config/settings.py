from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict

from flotilla.config.sources import ConfigurationSource
from flotilla.config.secrets import SecretsResolver
from flotilla.config.config_utils import ConfigUtils


class FlotillaSettings(BaseModel):
    """
    Immutable, validated configuration snapshot for a Flotilla application.
    """

    # Known top-level domains (all optional)
    core: Optional[Dict[str, Any]] = None
    agents: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, Any]] = None
    feature_flags: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(frozen=True, extra="allow")

    # ----------------------------
    # Factory methods
    # ----------------------------

    @classmethod
    def load(
        cls,
        *,
        sources: List["ConfigurationSource"],
        secrets_resolver: Optional["SecretsResolver"] = None,
    ) -> "FlotillaSettings":
        """
        Load configuration from one or more sources, merge, resolve secrets,
        and return an immutable FlotillaSettings instance.
        """
        merged: Dict[str, Any] = {}

        for source in sources:
            fragment = source.load()
            if fragment:
                merged = ConfigUtils.deep_merge(merged, fragment)

        if secrets_resolver:
            merged = secrets_resolver.resolve(merged)

        return cls.model_validate(merged)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlotillaSettings":
        """
        Convenience factory for tests and programmatic usage.
        """
        return cls.model_validate(data)
