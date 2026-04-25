from __future__ import annotations

import argparse
import json
import os
from typing import Any, Sequence

import httpx

from loan_client.http_client import LoanServerClient


DEFAULT_BASE_URL = os.getenv("LOAN_SERVER_BASE_URL", "http://127.0.0.1:8000")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="loan-client",
        description="CLI client for the Flotilla loan approval example server.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Base URL for the loan approval server. Defaults to %(default)s.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds. Defaults to %(default)s.",
    )
    parser.add_argument(
        "--user-id",
        default="loan-client",
        help="User identifier to attach to runtime requests. Defaults to %(default)s.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "create-thread",
        help="Create a new thread on the loan approval server.",
    )

    get_thread_parser = subparsers.add_parser(
        "get-thread",
        help="Fetch a thread and its entries from the loan approval server.",
    )
    get_thread_parser.add_argument("thread_id", help="Thread identifier to fetch.")

    subparsers.add_parser(
        "submit-loan",
        help="Interactively create a thread and submit a loan request.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    client = LoanServerClient(base_url=args.base_url, timeout=args.timeout)

    try:
        if args.command == "create-thread":
            payload = client.create_thread()
        elif args.command == "get-thread":
            payload = client.get_thread(args.thread_id)
        elif args.command == "submit-loan":
            payload = _submit_loan(client=client, user_id=args.user_id)
        else:
            parser.error(f"Unknown command: {args.command}")
            return 2
    except httpx.HTTPStatusError as exc:
        _print_error(
            f"Server returned {exc.response.status_code} for {exc.request.method} {exc.request.url}"
        )
        return 1
    except httpx.HTTPError as exc:
        _print_error(f"Request failed: {exc}")
        return 1

    if args.command == "submit-loan":
        _print_submission_result(payload)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _print_error(message: str) -> None:
    print(message)


def _submit_loan(*, client: LoanServerClient, user_id: str) -> dict[str, Any]:
    name = _prompt_non_empty("Applicant name: ")
    amount = _prompt_positive_float("Loan amount: ")

    thread = client.create_thread()
    thread_id = thread["thread_id"]
    initial_response = client.submit_loan_request(
        thread_id,
        user_id=user_id,
        name=name,
        amount=amount,
    )

    final_response = None
    resume_token = initial_response.get("resume_token")
    review_decision = None

    if initial_response.get("type") == "SUSPEND":
        review_decision = _prompt_review_decision("Review decision [approve/reject]: ")
        final_response = client.submit_loan_review(
            thread_id,
            user_id=user_id,
            resume_token=resume_token,
            decision=review_decision,
        )

    return {
        "thread_id": thread_id,
        "request": {
            "name": name,
            "amount": amount,
        },
        "initial_response": initial_response,
        "resume_token": resume_token,
        "review_decision": review_decision,
        "final_response": final_response,
    }


def _prompt_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("A value is required.")


def _prompt_positive_float(prompt: str) -> float:
    while True:
        raw = input(prompt).strip()
        try:
            value = float(raw)
        except ValueError:
            print("Enter a numeric loan amount.")
            continue

        if value <= 0:
            print("Enter a positive loan amount.")
            continue

        return value


def _prompt_review_decision(prompt: str) -> str:
    while True:
        value = input(prompt).strip().lower()
        if value in {"approve", "reject"}:
            return value
        print("Enter either 'approve' or 'reject'.")


def _print_submission_result(payload: dict[str, Any]) -> None:
    initial_response = payload["initial_response"]
    print(f"Thread ID: {payload['thread_id']}")
    print(f"Status: {initial_response['type']}")
    if payload.get("resume_token"):
        print(f"Resume Token: {payload['resume_token']}")
    print("Agent response:")
    print(_content_to_text(initial_response.get("content", [])))

    if payload.get("review_decision") and payload.get("final_response"):
        final_response = payload["final_response"]
        print(f"Review Decision: {payload['review_decision']}")
        print(f"Final Status: {final_response['type']}")
        print("Final Agent response:")
        print(_content_to_text(final_response.get("content", [])))


def _content_to_text(content: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for part in content:
        part_type = part.get("type")
        if part_type == "text":
            lines.append(part.get("text", ""))
        else:
            lines.append(json.dumps(part, indent=2, sort_keys=True))

    return "\n".join(line for line in lines if line) or "(no content)"


if __name__ == "__main__":
    raise SystemExit(main())
