from typing import Any, Dict, Mapping


class FlotillaSettings:
    """
    Immutable, semantically validated configuration snapshot
    for a Flotilla application.
    """

    def __init__(self, raw: Dict[str, Any]):
        self._raw = raw
        self._validate()

    # ----------------------------
    # Public access
    # ----------------------------

    @property
    def config(self) -> Mapping[str, Any]:
        return self._raw

    def get(self, key: str, default: Any = None) -> Any:
        return self._raw.get(key, default)

    # ----------------------------
    # Validation
    # ----------------------------

    def _validate(self) -> None:
        """
        Enforce Flotilla semantic invariants.
        Raise ValueError (or domain-specific errors) on failure.
        """
        # intentionally minimal to start
        pass
