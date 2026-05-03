from enum import Enum


class TelemetryType(str, Enum):

    RUNTIME_PHASE_STARTED = "runtime.phase.started"
    RUNTIME_PHASE_COMPLETED = "runtime.phase.completed"
    RUNTIME_PHASE_SUSPENDED = "runtime.phase.suspended"
    RUNTIME_PHASE_FAILED = "runtime.phase.failed"
    RUNTIME_THREAD_NOT_FOUND = "runtime.thread.not_found"
    RUNTIME_ACTIVE_THREAD_REJECTED = "runtime.active_thread.rejected"
    RUNTIME_RESUME_REJECTED = "runtime.resume.rejected"
    RUNTIME_TIMEOUT_CLOSED = "runtime.timeout.closed"

    AGENT_RUN_STARTED = "agent.run.started"
    AGENT_RUN_COMPLETED = "agent.run.completed"
    AGENT_RUN_FAILED = "agent.run.failed"


class TelemetryComponent(str, Enum):
    CONFIG_LOADER = "CONFIG_LOADER"
    COMPONENT_COMPILER = "COMPONENT_COMPILER"
    CONTAINER = "FLOTILLA_CONTAINER"
    RUNTIME = "FLOTILLA_RUNTIME"
    APPLICATION = "FLOTILLA_APPLICATION"
    AGENT = "FLOTILLA_AGENT"
