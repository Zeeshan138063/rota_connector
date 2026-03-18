"""
Custom exceptions for ROTA Connector SDK

Mirrors the HTTP → domain exception mapping pattern from auth31_connector,
extended with ROTA-specific scheduling domain errors.

Copyright (c) 2026 31 Green. All rights reserved.
This software is proprietary and confidential.
Unauthorized copying or distribution is strictly prohibited.
"""

from typing import Any


class RotaError(Exception):
    """
    Base exception for all ROTA Connector SDK errors.

    All SDK-raised exceptions inherit from this class, making it easy
    for consumers to catch all ROTA errors with a single except clause.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"status_code={self.status_code})"
        )


# ── HTTP-mapped exceptions ────────────────────────────────────────────────────

class AuthenticationError(RotaError):
    """Raised when authentication fails (HTTP 401).

    Typically means the client credentials are missing or invalid.
    Resolve by calling authenticate_with_management_credentials() again.
    """
    pass


class AuthorizationError(RotaError):
    """Raised when the caller lacks permission to perform an operation (HTTP 403)."""
    pass


class ResourceNotFoundError(RotaError):
    """Raised when a requested resource does not exist (HTTP 404)."""
    pass


class ValidationError(RotaError):
    """Raised when request payload fails server-side validation (HTTP 400 / 422)."""
    pass


class ConflictError(RotaError):
    """Raised when an operation conflicts with existing state (HTTP 409).

    Common cause: overlapping assignment slots, duplicate schedule entries.
    """
    pass


class RateLimitError(RotaError):
    """Raised when the API rate limit is exceeded (HTTP 429)."""
    pass


class ServerError(RotaError):
    """Raised when ROTA Core Service returns a 5xx error."""
    pass


# ── Provider / interface exceptions ──────────────────────────────────────────

class ProviderError(RotaError):
    """
    Base exception for errors raised by IResourceProvider or IContextProvider
    implementations in the consuming application.

    Connectors must catch domain-specific errors from their ORM/database
    and re-raise as ProviderError (or a subclass) so the SDK can handle them
    uniformly.
    """
    pass


class EntityNotFoundError(ProviderError):
    """Raised by a provider when a requested entity (staff/resource) does not exist."""
    pass


class ContextNotFoundError(ProviderError):
    """Raised by a provider when a requested context (practice/location) does not exist."""
    pass


class ProviderUnavailableError(ProviderError):
    """Raised when the underlying data source (DB, external API) is unreachable."""
    pass


# ── Scheduling domain exceptions ─────────────────────────────────────────────

class AssignmentConflictError(RotaError):
    """
    Raised when creating/updating an assignment would create a scheduling conflict.

    Check `conflicting_assignment_ids` for the IDs of the blocking assignments.
    """

    def __init__(
        self,
        message: str,
        conflicting_assignment_ids: list[str] | None = None,
        status_code: int | None = None,
        response: dict[str, Any] | None = None,
    ):
        self.conflicting_assignment_ids = conflicting_assignment_ids or []
        super().__init__(message, status_code, response)


class RecurrenceError(RotaError):
    """Raised when a recurrence rule is malformed or produces an invalid schedule."""
    pass
