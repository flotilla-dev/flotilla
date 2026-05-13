import pytest

from flotilla.runtime.content_part import StructuredPart, TextPart
from flotilla.runtime.phase_context import PhaseContext
from flotilla.runtime.runtime_request import RuntimeRequest
from flotilla.suspend.permissive_resume_authorization_policy import PermissiveResumeAuthorizationPolicy
from flotilla.suspend.resume_service import DefaultResumeService
from flotilla.thread.thread_context import ThreadContext
from flotilla.thread.thread_entries import ResumeEntry, SuspendEntry, UserInput


class CapturingResumeAuthorizationPolicy:
    def __init__(self):
        self.calls = []

    async def is_authorized(self, *, payload, suspend_entry, phase_context):
        self.calls.append(
            {
                "payload": payload,
                "suspend_entry": suspend_entry,
                "phase_context": phase_context,
            }
        )
        return True


@pytest.mark.asyncio
async def test_build_resume_entry_allows_new_phase_context_for_resume_request():
    service = DefaultResumeService(
        resume_authorization_policy=PermissiveResumeAuthorizationPolicy(),
        ttl_seconds=3600,
    )

    user = UserInput(
        thread_id="t1",
        phase_id="phase-start",
        entry_id="e1",
        actor_id="u1",
        content=[TextPart(text="hello")],
    )
    suspend = SuspendEntry(
        thread_id="t1",
        phase_id="phase-suspend",
        entry_id="e2",
        previous_entry_id="e1",
        actor_id="a1",
        content=[TextPart(text="approval required")],
    )
    thread_context = ThreadContext(entries=[user, suspend])

    resume_token = service.create_token(suspend)
    request = RuntimeRequest(
        thread_id="t1",
        user_id="reviewer-1",
        resume_token=resume_token,
        content=[
            StructuredPart(
                id="loan_review_decision",
                data={
                    "kind": "human_in_the_loop_resume",
                    "decision": "approve",
                    "decisions": [{"type": "approve"}],
                },
            )
        ],
    )
    phase_context = PhaseContext(
        thread_id="t1",
        phase_id="phase-resume-request",
        user_id="reviewer-1",
        agent_config={},
    )

    resume_entry = await service.build_resume_entry(
        request=request,
        phase_context=phase_context,
        thread_context=thread_context,
    )

    assert isinstance(resume_entry, ResumeEntry)
    assert resume_entry.phase_id == "phase-resume-request"
    assert resume_entry.previous_entry_id == "e2"
    assert resume_entry.actor_id == "reviewer-1"
    assert resume_entry.content[0].id == "loan_review_decision"


@pytest.mark.asyncio
async def test_build_resume_entry_passes_phase_context_to_authorization_policy():
    policy = CapturingResumeAuthorizationPolicy()
    service = DefaultResumeService(
        resume_authorization_policy=policy,
        ttl_seconds=3600,
    )

    suspend = SuspendEntry(
        thread_id="t1",
        phase_id="phase-suspend",
        entry_id="e2",
        previous_entry_id="e1",
        actor_id="a1",
        content=[TextPart(text="approval required")],
    )
    user = UserInput(
        thread_id="t1",
        phase_id="phase-start",
        entry_id="e1",
        actor_id="u1",
        content=[TextPart(text="hello")],
    )
    thread_context = ThreadContext(entries=[user, suspend])
    phase_context = PhaseContext(
        thread_id="t1",
        phase_id="phase-resume-request",
        user_id="reviewer-1",
        agent_config={},
    )
    request = RuntimeRequest(
        thread_id="t1",
        user_id="reviewer-1",
        resume_token=service.create_token(suspend),
        content=[TextPart(text="approved")],
    )

    await service.build_resume_entry(
        request=request,
        phase_context=phase_context,
        thread_context=thread_context,
    )

    assert len(policy.calls) == 1
    assert policy.calls[0]["phase_context"] is phase_context
    assert policy.calls[0]["phase_context"].user_id == "reviewer-1"
