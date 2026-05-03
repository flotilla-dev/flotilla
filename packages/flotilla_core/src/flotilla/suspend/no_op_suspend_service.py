from flotilla.suspend.suspend_service import SuspendService


class NoOpSuspendService(SuspendService):
    """
    Default suspend hook for apps that do not need external notification.

    FlotillaRuntime invokes SuspendService after a SuspendEntry is durable and
    a resume token exists. This implementation intentionally ignores that
    event, making suspend handling complete without notifying another system.
    """

    async def handle_suspend(self, thread_context, suspend_entry, resume_token, phase_context):
        pass
