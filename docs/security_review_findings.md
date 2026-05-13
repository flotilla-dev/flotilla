# Security Review Findings

This checklist captures the security review findings from May 4, 2026 so they can be resolved one at a time.

## Findings

1. [ ] High: Default resume tokens are forgeable.
   - `DefaultResumeService` used base64-encoded JSON without a signature.
   - Runtime defaulted to that service with a long TTL.
   - Current documentation intentionally calls this default insecure so tokens remain simple and portable across application instances and restarts.
   - App developers can use `ResumeAuthorizationPolicy` to add application-specific authorization checks against resume tokens and suspend entries.
   - Candidate 0.2 enhancement: add a cryptographically secure, database-backed resume-token implementation plus a matching authorization policy. Persisting token records would let secure resume validation work across application instances and restarts without changing `DefaultResumeService` semantics.

2. [x] Medium: Resume authorization policy has limited requester context.
   - `ResumeAuthorizationPolicy` intentionally receives only token payload and suspend entry, and the specification states that it does not enforce authentication mechanisms or define identity systems.
   - This is not a flaw if authentication and requester authorization are enforced upstream or by a custom `ResumeService`.
   - It is still an API ergonomics gap for applications that want policy-level checks such as comparing the authenticated requester to the suspended workflow, because `PhaseContext` is not passed to `is_authorized()`.
   - Candidate resolution: add `phase_context` to `ResumeAuthorizationPolicy.is_authorized()`. The authenticated/current user is already represented on `PhaseContext`, and passing that context keeps the policy focused without exposing the full `RuntimeRequest` payload.
   - Resolved May 7, 2026: `phase_context` is now passed to `ResumeAuthorizationPolicy.is_authorized()`.

3. [x] High: Loan approval example exposes unauthenticated workflow and audit endpoints.
   - Thread creation, thread loading, loan submission, and loan review endpoints are open.
   - `user_id` is client-supplied request body data.
   - Resolved May 7, 2026: accepted for the example app boundary and documented in the app README. The example remains intentionally unauthenticated so it can focus on Flotilla runtime behavior; production applications should enforce app-owned authentication/authorization and derive `user_id` from the authenticated requester.

4. [x] Medium: Thread history endpoint discloses all durable workflow content.
   - `GET /threads/{thread_id}` returns every serialized entry.
   - This can expose model output, tool results, suspend payloads, and entry ids.
   - Resolved May 7, 2026: accepted for the loan approval example boundary and documented in the app README. Production applications should gate and redact thread-history responses according to caller authorization.

5. [x] Medium: Starlette pin is affected by known DoS advisories.
   - `flotilla-fastapi` pins `starlette = "0.46.0"`.
   - Known affected ranges include versions below `0.49.1` for a `FileResponse` Range-header ReDoS and below `0.47.2` for multipart upload resource exhaustion.
   - Resolved May 7, 2026: `flotilla-fastapi` now requires Starlette `>=0.49.1,<0.50.0`.

6. [ ] Medium: Request and content sizes are effectively unbounded.
   - `RuntimeRequest.content` only enforces `min_length=1`.
   - `StructuredPart.data` accepts arbitrary payloads.
   - SQL stores serialized payloads as unrestricted `TEXT`.

7. [x] Medium: LangChain adapter returns raw exception messages to users and durable state.
   - Agent execution exceptions are converted to `TextPart(text=str(e))`.
   - This may leak provider errors, tool details, connection strings, or paths.
   - Resolved May 7, 2026: LangChain agent errors now emit a generic user-facing message while preserving detailed exception information in logs.

8. [x] Low/Medium: Weather example builds URLs manually and uses requests without timeouts.
   - User-controlled values are interpolated into query strings.
   - `requests.get()` calls have no timeout.
   - Resolved May 7, 2026: weather tools now pass query parameters through `requests` and set explicit request timeouts.

9. [x] Low: Reflection-based construction must be treated as trusted-config only.
   - `ReflectionProvider` imports and instantiates configured class paths.
   - This is expected for trusted IoC configuration but unsafe for tenant/user-controlled config.
   - Resolved May 7, 2026: configuration documentation now states that Flotilla configuration is trusted application code and must not be accepted directly from tenant/user-controlled input.
