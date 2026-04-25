from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class LoanServerClient:
    base_url: str
    timeout: float = 10.0

    def create_thread(self) -> dict[str, Any]:
        return self._request("POST", "/threads")

    def get_thread(self, thread_id: str) -> dict[str, Any]:
        return self._request("GET", f"/threads/{thread_id}")

    def submit_loan_request(self, thread_id: str, *, user_id: str, name: str, amount: float) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/threads/{thread_id}/loan-request",
            json={
                "user_id": user_id,
                "name": name,
                "amount": amount,
            },
        )

    def submit_loan_review(self, thread_id: str, *, user_id: str, resume_token: str, decision: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/threads/{thread_id}/loan-review",
            json={
                "user_id": user_id,
                "resume_token": resume_token,
                "decision": decision,
            },
        )

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            response = client.request(method, path, json=json)
            response.raise_for_status()
            return response.json()
