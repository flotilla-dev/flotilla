class FlotillaConfigurationError(ValueError):
    """
    Raised when Flotilla configuration is present but invalid.

    This indicates a user-facing configuration error (e.g. missing required
    fields, unknown builders, invalid values), not a framework bug.
    """


class ConfigurationResolutionError(FlotillaConfigurationError):
    """
    Raised when Flotilla is unable to resolve $config tag into configuration block
    """


class SecretResolutionError(FlotillaConfigurationError):
    """
    Raised when the list SecretResolver(s) are unable to convert a $secret into a value
    """


class ReferenceResolutionError(FlotillaConfigurationError):
    """
    Raised when Flotilla is unable to convert a $ref into a container component
    """


class ComponentResolutionError(FlotillaConfigurationError):
    """
    Raised when Flotilla is unable to find an object in the container
    """
