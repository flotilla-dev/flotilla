from flotilla.core.thread_context import ThreadStatus


class FlotillaAgentError(RuntimeError):
    pass


class ThreadNotRunnableError(FlotillaAgentError):
    def __init__(self, thread_id: str, status: ThreadStatus):
        super().__init__(f"Thread {thread_id} is not runnable (status={status}).")
        self.status = status


class ThreadIdMismatchError(FlotillaAgentError):
    def __init__(self, expected: str, actual: str):
        super().__init__(
            f"ExecutionConfig.thread_id ({expected}) does not match "
            f"ThreadContext.thread_id ({actual})."
        )
        self.expected = expected
        self.actual = actual


class InvalidAgentEventError(FlotillaAgentError):
    pass
