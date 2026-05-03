# Loan Approval CLI Client

CLI client for the Flotilla loan approval example server.

## What This Example Demonstrates

The client drives the full loan approval workflow exposed by the example app. It creates durable threads, submits loan requests, and handles the human-in-the-loop approval step when the agent interrupts for review.

Together with the server, this example demonstrates a fully integrated Flotilla stack across `flotilla-core`, `flotilla-sql`, `flotilla-langchain`, and `flotilla-fastapi`. The workflow can pause for an approval or rejection decision, then resume using state stored durably in PostgreSQL across sessions and server processes.

## Requirements

- Python 3.11 or newer
- Poetry
- The loan approval app running locally, or a reachable loan approval server URL

The client does not need an OpenAI API key or database connection. Those are configured on the app server.

## Install Dependencies

From this directory:

```bash
poetry install
```

## Run the Client

Start the loan approval app first. By default, the client sends requests to `http://127.0.0.1:8000`.

Submit an interactive loan request:

```bash
poetry run loan-client submit-loan
```

If the server suspends for human review, the CLI prompts for an `approve` or `reject` decision and resumes the request.

## Use a Different Server URL

Pass `--base-url` on any command:

```bash
poetry run loan-client --base-url http://127.0.0.1:8000 create-thread
```

Or set `LOAN_SERVER_BASE_URL`:

```bash
LOAN_SERVER_BASE_URL=http://127.0.0.1:8000 poetry run loan-client create-thread
```
