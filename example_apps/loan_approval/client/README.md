# Loan Approval CLI Client

Install with Poetry:

```bash
poetry install
```

Run the CLI against a local server:

```bash
poetry run loan-client create-thread
poetry run loan-client get-thread <thread-id>
```

You can override the server URL with `--base-url` or `LOAN_SERVER_BASE_URL`.
