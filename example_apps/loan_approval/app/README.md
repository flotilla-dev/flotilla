# Loan Approval App

FastAPI server for the Flotilla loan approval example.

## What This Example Demonstrates

This example shows the Flotilla stack working as an integrated application:

- `flotilla-core` provides the runtime, thread model, configuration, and orchestration primitives.
- `flotilla-langchain` connects the workflow to an OpenAI-backed LangChain agent.
- `flotilla-fastapi` exposes the runtime as HTTP endpoints.
- `flotilla-sql` persists thread entries through PostgreSQL.

The workflow models an agentic loan approval process. A user submits a loan request, the agent evaluates the request with tools, and the run can interrupt for human review. The reviewer then approves or rejects the request, and the agent resumes from the suspended point.

The SQL integration makes the example especially useful: thread history and checkpoints are stored durably in PostgreSQL, so work can survive across requests, sessions, and server processes.

## Requirements

- Python 3.11 or newer
- Poetry
- A local PostgreSQL database
- An OpenAI API key

The app stores thread entries and LangGraph checkpoints in PostgreSQL. The database named in the connection strings must exist before the app starts. The Flotilla thread-store tables must also be created before running the app. This example uses a PostgreSQL schema named `flotilla` for both the Flotilla SQL thread store and the LangGraph checkpointer.

## Set Up PostgreSQL

Run a local PostgreSQL server that is reachable from the connection strings in `.env`. The example `.env` below expects a database named `flotilla_db`.

Create the database if it does not already exist:

```bash
createdb flotilla_db
```

Create the shared `flotilla` schema:

```bash
psql -d flotilla_db -c "CREATE SCHEMA IF NOT EXISTS flotilla;"
```

Create the Flotilla SQL thread-store tables in that schema:

```bash
PGOPTIONS='-c search_path=flotilla' \
  psql -d flotilla_db -f ../../../packages/flotilla_sql/src/flotilla_sql/thread/schema/thread_entry_store.sql
```

That schema file lives in the `flotilla_sql` package at:

```text
packages/flotilla_sql/src/flotilla_sql/thread/schema/thread_entry_store.sql
```

It creates the `thread`, `thread_entry`, and `content_part` tables used by `flotilla-sql` to store durable thread history. The SQL file does not set a PostgreSQL schema, so the tables are created in the connection's active schema. The `PGOPTIONS` command above sets that schema to `flotilla`.

If your local PostgreSQL user, password, host, port, or database name differs from the example values below, update both connection strings to match your setup. For example, pass the same connection details to `createdb` and `psql` that you put in `.env`.

## Configure Environment

Create a `.env` file in this directory:

```bash
OPENAI_API_KEY=<api_key>
SQL_PSYCOPG_CONNECTION=postgresql://<db_user>:<user_password>@172.21.48.1:5432/flotilla_db
SQL_ASYNC_CONNECTION=postgresql+asyncpg://<db_user>:<user_password>@172.21.48.1:5432/flotilla_db?options=-csearch_path%3Dflotilla
```

`SQL_PSYCOPG_CONNECTION` is used by the LangGraph Postgres checkpointer. `SQL_ASYNC_CONNECTION` is used by the Flotilla SQL thread store, and the `options` query parameter sets the SQLAlchemy/asyncpg connection search path to the `flotilla` schema.

## Install Dependencies

From this directory:

```bash
poetry install
```

## Run the Server

From this directory:

```bash
poetry run python -m loan_server.start
```

By default the FastAPI server listens on `http://127.0.0.1:8000`.

## Try the API

With the server running:

```bash
curl -X POST http://127.0.0.1:8000/threads
```

Use the returned `thread_id` with the loan approval client or the server endpoints:

```bash
curl -X POST http://127.0.0.1:8000/threads/<thread-id>/loan-request \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"loan-client","name":"Ada Lovelace","amount":50000}'
```

## Security Note

This is a framework integration example, not a production API boundary. The loan approval endpoints are intentionally small and unauthenticated so the example stays focused on Flotilla runtime, persistence, and suspend/resume behavior. The `GET /threads/{thread_id}` endpoint returns serialized durable workflow entries for demonstration and audit inspection, including content that may be sensitive in real systems. A production application should put these routes behind application-owned authentication and authorization, redact or narrow thread-history responses for each caller, and derive `user_id` from the authenticated requester rather than accepting it directly from request bodies.

## Run Tests

```bash
poetry run pytest
```
