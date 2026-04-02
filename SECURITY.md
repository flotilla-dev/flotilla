# Security Policy

## Reporting a Vulnerability

If you believe you have found a security vulnerability in Flotilla, please **do not open a public GitHub issue**.

Instead, report the issue privately by emailing:

**geoffschneider@gmail.com**  <!-- replace if you want a different email -->

Please include as much detail as possible to help us understand and reproduce the issue:

- a description of the vulnerability
- steps to reproduce the issue
- any relevant code, logs, or configuration
- potential impact and affected components (if known)

We will acknowledge receipt of your report as soon as possible.

---

## Scope

Security vulnerabilities may include (but are not limited to):

- vulnerabilities in runtime execution or orchestration logic
- unsafe handling of user input or tool execution
- injection risks (prompt injection, code execution, etc.)
- authentication or authorization issues (where applicable)
- data leakage or improper handling of sensitive data
- dependency vulnerabilities that materially affect the project

If you are unsure whether something qualifies as a security issue, it is always better to report it.

---

## Response Process

We aim to:

- acknowledge reports promptly
- investigate and validate the issue
- determine severity and impact
- develop and release a fix where appropriate
- coordinate responsible disclosure when applicable

Response and resolution times may vary depending on the complexity of the issue.

---

## Disclosure Policy

Please do not publicly disclose security vulnerabilities until they have been reviewed and addressed.

We will work with you to coordinate responsible disclosure once a fix is available.

---

## Supported Versions

Flotilla is currently in early development (pre-1.0).

Security fixes will be applied to the latest version of the project. Older versions may not receive patches.

---

## Dependencies

Flotilla relies on third-party dependencies. Known vulnerabilities in dependencies should also be reported if they impact Flotilla usage.

Where possible, we will update or mitigate affected dependencies in a timely manner.

---

## Acknowledgements

We appreciate responsible disclosure and will acknowledge contributors who report valid security issues, unless they prefer to remain anonymous.