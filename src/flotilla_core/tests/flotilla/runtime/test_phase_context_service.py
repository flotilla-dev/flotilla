import uuid
import pytest
from typing import Dict, Any

# Adjust imports to your actual module paths
from flotilla.runtime.phase_context import PhaseContext
from flotilla.runtime.phase_context_service import PhaseContextService
from flotilla.runtime.runtime_request import RuntimeRequest
from flotilla.runtime.content_part import TextPart


def test_create_phase_context_basic():
    service = PhaseContextService()
    request = RuntimeRequest(thread_id="t1", user_id="u1", content=[TextPart(text="test")])

    phase_context = service.create_phase_context(request)

    assert phase_context.thread_id == "t1"
    assert phase_context.user_id == "u1"
    assert isinstance(phase_context.phase_id, str)
    assert phase_context.agent_config == {}


def test_phase_id_is_unique():
    service = PhaseContextService()
    request = RuntimeRequest(thread_id="t1", user_id="u1", content=[TextPart(text="test")])

    p1 = service.create_phase_context(request)
    p2 = service.create_phase_context(request)

    assert p1.phase_id != p2.phase_id


def test_agent_config_override():
    class CustomPhaseContextService(PhaseContextService):
        def _create_agent_config(self, request: RuntimeRequest) -> Dict[str, Any]:
            return {"temperature": 0.5}

    service = CustomPhaseContextService()
    request = RuntimeRequest(thread_id="t1", user_id="u1", content=[TextPart(text="test")])

    phase_context = service.create_phase_context(request)

    assert phase_context.agent_config == {"temperature": 0.5}
