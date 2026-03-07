from flotilla.flotilla_error import FlotillaError


class ResumeTokenInvalidError(FlotillaError):
    pass


class ResumeTokenExpiredError(FlotillaError):
    pass


class ResumeAuthorizationError(FlotillaError):
    pass
