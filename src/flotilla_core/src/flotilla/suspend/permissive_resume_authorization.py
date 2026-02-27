from flotilla.suspend.resume_authorization_policy import ResumeAuthorizationPolicy


class PermissiveResumeAuthorization(ResumeAuthorizationPolicy):

    def is_authorized(self, *, request, suspend_entry):
        return True
