from flotilla.suspend.resume_authorization_policy import ResumeAuthorizationPolicy


class PermissiveResumeAuthorizationPolicy(ResumeAuthorizationPolicy):
    """
    Default authorization policy for deployments without resume restrictions.

    DefaultResumeService calls this after token structure, expiration, thread
    id, and durable SuspendEntry matching have already succeeded. This policy
    answers only the final permission question and always allows the resume.
    """

    async def is_authorized(self, *, payload, suspend_entry, phase_context):
        return True
