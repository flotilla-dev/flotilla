from flotilla.runtime.phase_context import PhaseContext
from flotilla.runtime.runtime_request import RuntimeRequest
import uuid
from typing import Dict, Any


class PhaseContextService:
    """
    Factory service responsible for creating PhaseContext instances
    for each execution phase.

    This service generates a new unique phase_id and provides a hook
    for supplying optional agent-specific configuration via
    `_create_agent_config`.

    Applications may subclass this service to customize how
    phase-level configuration is derived from a RuntimeRequest.

    The default implementation provides no agent-specific overrides.
    """

    def create_phase_context(self, request: RuntimeRequest) -> PhaseContext:
        """
        Simple factory style method that creates a PhaseContext from the supplied RuntimeRequest
        """
        return PhaseContext(
            thread_id=request.thread_id,
            phase_id=str(uuid.uuid4()),
            user_id=request.user_id,
            correlation_id=request.correlation_id,
            trace_id=request.trace_id,
            agent_config=self._create_agent_config(request=request),
        )

    def _create_agent_config(self, request: RuntimeRequest) -> Dict[str, Any]:
        """
        Create optional agent-specific configuration for the execution phase.

        Subclasses may override this method to derive configuration values
        (e.g., model parameters, execution limits, feature flags) from the
        provided RuntimeRequest.

        The returned dictionary is passed through to the AgentAdapter
        implementation and interpreted according to the specific agent
        library in use.

        The base implementation returns an empty dictionary.
        """
        return {}
