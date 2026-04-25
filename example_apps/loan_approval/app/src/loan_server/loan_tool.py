from flotilla.tools.flotilla_tool import FlotillaTool
from typing import Callable
import uuid


class LoanProcessingTool(FlotillaTool):

    @property
    def name(self) -> str:
        return "loan_processing_tool"

    @property
    def llm_description(self) -> str:
        return """Use this tool to record the loan processing state after risk has been assessed.
        Call this AFTER risk_assessment_tool.
        Inputs:
        - user_id (string)
        - loan_amount (number)
        - risk_score (number)
        - risk_level (string)
        - status (string, use PENDING_REVIEW unless an explicit human approval decision is provided)
        You MUST call this tool to complete processing.
        Do NOT invent approval or rejection decisions on your own.
        Returns a JSON object containing the stored loan record."""

    @property
    def execution_callable(self) -> Callable:
        return self.process_loan

    # storage for example use only.  Production should NOT store locally but instead would
    # write to a database
    _store = []

    async def process_loan(
        self,
        user_id: str,
        loan_amount: float,
        risk_score: int,
        risk_level: str,
        status: str = "PENDING_REVIEW",
    ) -> dict:
        record = {
            "loan_id": str(uuid.uuid4()),
            "user_id": user_id,
            "loan_amount": loan_amount,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "status": status,
        }

        self._store.append(record)

        return record

    @classmethod
    def get_all(cls):
        return cls._store
