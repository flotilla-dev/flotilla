class FlotillaConfigurationError(ValueError):
    """
    Raised when Flotilla configuration is present but invalid.

    This indicates a user-facing configuration error (e.g. missing required
    fields, unknown builders, invalid values), not a framework bug.
    """