import base64
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from flotilla.utils.logger import get_logger
from flotilla.thread.thread_entries import SuspendEntry, ResumeEntry
from flotilla.thread.thread_context import ThreadContext
from flotilla.runtime.runtime_request import RuntimeRequest
from flotilla.runtime.phase_context import PhaseContext
from flotilla.suspend.errors import ResumeAuthorizationError, ResumeTokenExpiredError, ResumeTokenInvalidError
from flotilla.suspend.resume_authorization_policy import ResumeAuthorizationPolicy
from flotilla.suspend.resume_token_payload import ResumeTokenPayload

logger = get_logger(__name__)


class ResumeService(ABC):
    """
    Service that owns resume-token mechanics in the runtime flow.

    During suspend handling, FlotillaRuntime asks this service to create the
    token returned to the caller. During resume handling, the runtime asks it
    to validate the supplied token against the current durable ThreadContext
    and construct the ResumeEntry that should be appended.

    Implementations own token encoding, token expiration, and token-to-thread
    validation. Authorization decisions should be delegated to a
    ResumeAuthorizationPolicy so the service remains focused on resume flow.
    """

    @abstractmethod
    def create_token(self, suspend_entry: SuspendEntry) -> str: ...

    @abstractmethod
    async def build_resume_entry(
        self,
        request: RuntimeRequest,
        phase_context: PhaseContext,
        thread_context: ThreadContext,
    ) -> ResumeEntry: ...


class DefaultResumeService(ResumeService):
    """
    Default ResumeService implementation.

    Tokens are Base64 encoded JSON payloads. This implementation is
    intentionally simple and not cryptographically secure.

    Subclasses may override `_encode_token()` and `_decode_token()` to
    provide secure token implementations (JWT, HMAC, etc).
    """

    def __init__(self, resume_authorization_policy: ResumeAuthorizationPolicy, ttl_seconds: int = 3600):
        self._auth_policy = resume_authorization_policy
        self._ttl = ttl_seconds

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def create_token(self, suspend_entry: SuspendEntry) -> str:
        now = datetime.now(timezone.utc)

        payload = ResumeTokenPayload(
            thread_id=suspend_entry.thread_id,
            phase_id=suspend_entry.phase_id,
            suspend_entry_id=suspend_entry.entry_id,
            issued_at=now,
            expires_at=now + timedelta(seconds=self._ttl),
        )

        logger.info(
            "Create resume token for suspend entry '%s' on thread '%s'",
            suspend_entry.entry_id,
            suspend_entry.thread_id,
        )

        return self._encode_token(payload)

    async def build_resume_entry(
        self,
        request: RuntimeRequest,
        phase_context: PhaseContext,
        thread_context: ThreadContext,
    ) -> ResumeEntry:
        """
        Validates resume token and authorization and constructs
        the ResumeEntry to append to the thread.

        Raises:
            ResumeTokenInvalidError
            ResumeTokenExpiredError
            ResumeAuthorizationError
        """

        logger.debug("Build resume entry for thread '%s' phase '%s'", request.thread_id, phase_context.phase_id)
        payload = self._decode_token(request.resume_token)

        # Validate thread id
        if payload.thread_id != request.thread_id:
            logger.warning(
                "Resume token thread mismatch: request thread '%s' token thread '%s'",
                request.thread_id,
                payload.thread_id,
            )
            raise ResumeTokenInvalidError("Thread mismatch")

        # Validate expiration
        now = datetime.now(timezone.utc)
        if payload.expires_at < now:
            logger.warning(
                "Resume token expired for thread '%s' suspend entry '%s'",
                payload.thread_id,
                payload.suspend_entry_id,
            )
            raise ResumeTokenExpiredError("Resume token expired")

        # Locate SuspendEntry
        if not isinstance(thread_context.last_entry, SuspendEntry):
            logger.warning(
                "Resume token rejected because thread '%s' is not currently suspended",
                request.thread_id,
            )
            raise ResumeTokenInvalidError("SuspendEntry is not tail of ThreadContext")

        if thread_context.last_entry.entry_id != payload.suspend_entry_id:
            logger.warning(
                "Resume token suspend entry mismatch for thread '%s': tail '%s' token '%s'",
                request.thread_id,
                thread_context.last_entry.entry_id,
                payload.suspend_entry_id,
            )
            raise ResumeTokenInvalidError("Entry ID of token does not match SuspendEntry ID")

        if not await self._auth_policy.is_authorized(
            payload=payload,
            suspend_entry=thread_context.last_entry,
            phase_context=phase_context,
        ):
            logger.warning(
                "Resume authorization denied for thread '%s' suspend entry '%s'",
                request.thread_id,
                thread_context.last_entry.entry_id,
            )
            raise ResumeAuthorizationError("User is not authorized to resume execution")

        # Build ResumeEntry
        logger.info(
            "Resume token accepted for thread '%s' suspend entry '%s'",
            request.thread_id,
            thread_context.last_entry.entry_id,
        )
        return ResumeEntry(
            thread_id=request.thread_id,
            phase_id=phase_context.phase_id,
            previous_entry_id=thread_context.last_entry.entry_id,
            content=request.content,
            actor_id=request.user_id,
        )

    # ---------------------------------------------------------
    # Extension hooks
    # ---------------------------------------------------------

    def _encode_token(self, payload: ResumeTokenPayload) -> str:
        json_bytes = payload.model_dump_json().encode("utf-8")
        return base64.urlsafe_b64encode(json_bytes).decode("utf-8")

    def _decode_token(self, token: str) -> ResumeTokenPayload:
        try:
            json_bytes = base64.urlsafe_b64decode(token.encode("utf-8"))
            payload_dict = json.loads(json_bytes.decode("utf-8"))
            return ResumeTokenPayload(**payload_dict)
        except Exception as ex:
            logger.warning("Resume token could not be decoded or validated")
            raise ResumeTokenInvalidError("Resume token could not be decoded") from ex
