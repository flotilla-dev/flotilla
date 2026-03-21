from flotilla.suspend.suspend_policy import SuspendPolicy


class NoOpSuspend(SuspendPolicy):

    def handle_suspend(thread_context, suspend_entry, resume_token, execution_config):
        pass
