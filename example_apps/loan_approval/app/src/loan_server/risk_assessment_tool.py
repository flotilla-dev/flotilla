from flotilla.tools.flotilla_tool import FlotillaTool
from typing import Callable


class RiskAssessmentTool(FlotillaTool):
    @property
    def name(self) -> str:
        return "risk_assessment_tool"

    @property
    def llm_description(self) -> str:
        return """
        Use this tool to evaluate the risk of a loan request.
        Inputs: user_id (string), loan_amount (number). 
        Returns a JSON object containing: user_id, loan_amount, risk_score (1-10, where lower is higher risk), 
        and risk_level (LOW_RISK, MEDIUM_RISK, HIGH_RISK).
        """

    @property
    def execution_callable(self) -> Callable:
        return self.assess_risk

    def assess_risk(self, loan_amount: float, user_id: str) -> dict:
        if loan_amount <= 1_000:
            score = 10
        elif loan_amount <= 5_000:
            score = 8
        elif loan_amount <= 10_000:
            score = 6
        elif loan_amount <= 25_000:
            score = 4
        else:
            score = 2

        return {
            "user_id": user_id,
            "loan_amount": loan_amount,
            "risk_score": score,
            "risk_level": self._label(score),
        }

    def _label(self, score: int) -> str:
        if score >= 8:
            return "LOW_RISK"
        elif score >= 5:
            return "MEDIUM_RISK"
        else:
            return "HIGH_RISK"
