"""Application exception taxonomy. Safety paths fail closed (R46)."""
from __future__ import annotations


class AegisError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str = "", *, details: dict | None = None):
        super().__init__(message or self.code)
        self.details = details or {}


class ConflictError(AegisError):
    status_code = 409
    code = "state_conflict"


class NotFoundError(AegisError):
    status_code = 404
    code = "not_found"


class ValidationFailed(AegisError):
    status_code = 422
    code = "validation_failed"


class AuthError(AegisError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AegisError):
    status_code = 403
    code = "forbidden"


class RateLimited(AegisError):
    status_code = 429
    code = "rate_limited"


class ServiceUnavailable(AegisError):
    status_code = 503
    code = "service_unavailable"


class ExecHashMismatch(AegisError):
    """INV-005: approved/validated/executed content diverged. HARD BLOCK."""

    status_code = 409
    code = "EXEC_HASH_MISMATCH"
