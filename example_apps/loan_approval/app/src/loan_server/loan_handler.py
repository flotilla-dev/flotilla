from pydantic import BaseModel, Field

from flotilla.runtime.content_part import StructuredPart
from flotilla.runtime.flotilla_runtime import FlotillaRuntime
from flotilla.runtime.runtime_request import RuntimeRequest
from flotilla.runtime.runtime_response import RuntimeResponse
from flotilla_fastapi.handler import HTTPHandler
from flotilla_fastapi.routes import routes


class SubmitLoanRequest(BaseModel):
    user_id: str = Field(default="loan-client")
    name: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)


class SubmitLoanReviewRequest(BaseModel):
    user_id: str = Field(default="loan-client")
    resume_token: str = Field(..., min_length=1)
    decision: str = Field(..., pattern="^(approve|reject)$")


class LoanHandler(HTTPHandler):
    def __init__(self, runtime: FlotillaRuntime):
        self._runtime = runtime

    @routes.post("/threads/{thread_id}/loan-request")
    async def submit_loan_request(self, thread_id: str, request: SubmitLoanRequest) -> RuntimeResponse:
        loan_request = StructuredPart(
            data={
                "name": request.name,
                "amount": request.amount,
            }
        )
        runtime_request = RuntimeRequest(
            thread_id=thread_id,
            user_id=request.user_id,
            content=[loan_request],
        )
        return await self._runtime.run(runtime_request)

    @routes.post("/threads/{thread_id}/loan-review")
    async def submit_loan_review(self, thread_id: str, request: SubmitLoanReviewRequest) -> RuntimeResponse:
        review_decision = StructuredPart(
            id="loan_review_decision",
            data={
                "kind": "human_in_the_loop_resume",
                "decision": request.decision,
                "decisions": [{"type": request.decision}],
            },
        )
        runtime_request = RuntimeRequest(
            thread_id=thread_id,
            user_id=request.user_id,
            resume_token=request.resume_token,
            content=[review_decision],
        )
        return await self._runtime.run(runtime_request)
