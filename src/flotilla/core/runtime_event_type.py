from enum import Enum

class RuntimeEventType(str, Enum):
    """
    Canonical event types emitted by Flotilla runtimes.

    These events describe execution progress, control flow,
    suspension, and completion.
    """

    # ─────────────────────────────────────────────
    # Progress / informational events
    # ─────────────────────────────────────────────

    START = "start"
    """Execution has started (or resumed)."""

    AGENT_SELECTED = "agent_selected"
    """An agent has been selected for execution."""

    AGENT_STARTED = "agent_started"
    """An agent has begun execution."""

    AGENT_COMPLETED = "agent_completed"
    """An agent has completed execution."""

    STEP_STARTED = "step_started"
    """A logical execution step has begun."""

    STEP_COMPLETED = "step_completed"
    """A logical execution step has completed."""

    MESSAGE = "message"
    """A high-level message emitted by an agent (non-streaming)."""

    TOKEN = "token"
    """A streamed token or chunk of output."""

    TOOL_CALL = "tool_call"
    """A tool invocation has been requested."""

    TOOL_RESULT = "tool_result"
    """A tool invocation has completed."""

    # ─────────────────────────────────────────────
    # Control / interruption events
    # ─────────────────────────────────────────────

    AWAIT_INPUT = "await_input"
    """
    Execution is suspended pending external input
    (human-in-the-loop or system response).
    Carries an ExecutionCheckpoint.
    """

    INTERRUPT = "interrupt"
    """
    Execution was intentionally interrupted by policy,
    safety, or runtime condition.
    Carries an ExecutionCheckpoint.
    """

    # ─────────────────────────────────────────────
    # Terminal events
    # ─────────────────────────────────────────────

    COMPLETE = "complete"
    """Execution completed successfully."""

    ERROR = "error"
    """Execution failed with an error."""
