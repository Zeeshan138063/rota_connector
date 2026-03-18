"""
Base HTTP client for ROTA Connector SDK

Mirrors the BaseClient pattern from auth31_connector.
Handles HTTP transport, authentication headers, and maps
HTTP status codes to ROTA domain exceptions.

Copyright (c) 2026 31 Green. All rights reserved.
This software is proprietary and confidential.
Unauthorized copying or distribution is strictly prohibited.
"""

from typing import Any
from urllib.parse import urljoin

import httpx

from rota_connector.exceptions import (
    AssignmentConflictError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ResourceNotFoundError,
    RotaError,
    ServerError,
    ValidationError,
)


class BaseClient:
    """
    Core HTTP client providing authenticated requests to the ROTA Core Service.

    Design: lazy-initialised httpx.Client with connection pooling.
    All HTTP verbs (GET / POST / PUT / PATCH / DELETE) delegate here,
    so error handling is centralised in _handle_response().
    """

    def __init__(
        self,
        base_url:   str,
        timeout:    float | None = 30.0,
        verify_ssl: bool         = True,
    ):
        self.base_url   = base_url.rstrip("/")
        self.timeout    = timeout
        self.verify_ssl = verify_ssl
        self._client_id: str | None = None
        self._client_secret: str | None = None
        self._client:       httpx.Client | None = None

    # ── HTTP client ───────────────────────────────────────────────────────────

    @property
    def client(self) -> httpx.Client:
        """Return (or lazily create) the underlying httpx.Client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        return self._client

    # ── Auth ──────────────────────────────────────────────────────────────────

    def set_credentials(self, client_id: str, client_secret: str) -> None:
        """Set the Client ID and Secret used for all subsequent requests."""
        self._client_id = client_id
        self._client_secret = client_secret

    def clear_credentials(self) -> None:
        """Remove the current credentials (e.g. on logout)."""
        self._client_id = None
        self._client_secret = None

    # ── Request helpers ───────────────────────────────────────────────────────

    def _get_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept":       "application/json",
        }
        if self._client_id and self._client_secret:
            headers["X-ROTA-Client-ID"] = self._client_id
            headers["X-ROTA-Client-Secret"] = self._client_secret
        if extra:
            headers.update(extra)
        return headers

    def _build_url(self, endpoint: str) -> str:
        return urljoin(self.base_url + "/", endpoint.lstrip("/"))

    # ── Response / error handling ─────────────────────────────────────────────

    def _handle_response(self, response: httpx.Response) -> Any:
        """
        Raise a typed ROTA exception for non-2xx responses,
        or return the parsed JSON body for successful ones.
        """
        try:
            response.raise_for_status()

            if response.status_code == 204 or not response.content:
                return None

            return response.json()

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code

            try:
                err_data = exc.response.json()
                # Support both {"detail": "..."} and unified {"message": "..."} shapes
                message = (
                    err_data.get("message")
                    or err_data.get("detail")
                    or str(exc)
                )
            except Exception:
                err_data = None
                message  = str(exc)

            match status:
                case 401:
                    raise AuthenticationError(message, status, err_data) from exc
                case 403:
                    raise AuthorizationError(message, status, err_data) from exc
                case 404:
                    raise ResourceNotFoundError(message, status, err_data) from exc
                case 409:
                    conflict_ids = (err_data or {}).get("conflicting_assignment_ids", [])
                    raise AssignmentConflictError(
                        message, conflict_ids, status, err_data
                    ) from exc
                case 400 | 422:
                    raise ValidationError(message, status, err_data) from exc
                case 429:
                    raise RateLimitError(message, status, err_data) from exc
                case _ if status >= 500:
                    raise ServerError(message, status, err_data) from exc
                case _:
                    raise RotaError(message, status, err_data) from exc

    # ── HTTP verbs ────────────────────────────────────────────────────────────

    def get(
        self,
        endpoint: str,
        params:   dict[str, Any] | None    = None,
        headers:  dict[str, str] | None    = None,
    ) -> Any:
        url = self._build_url(endpoint)
        resp = self.client.get(url, params=params, headers=self._get_headers(headers))
        return self._handle_response(resp)

    def post(
        self,
        endpoint: str,
        params:   dict[str, Any] | None    = None,
        json:     dict[str, Any] | None    = None,
        data:     dict[str, Any] | None    = None,
        headers:  dict[str, str] | None    = None,
    ) -> Any:
        url = self._build_url(endpoint)
        resp = self.client.post(url, params=params, json=json, data=data, headers=self._get_headers(headers))
        return self._handle_response(resp)

    def put(
        self,
        endpoint: str,
        params:   dict[str, Any] | None    = None,
        json:     dict[str, Any] | None    = None,
        headers:  dict[str, str] | None    = None,
    ) -> Any:
        url = self._build_url(endpoint)
        resp = self.client.put(url, params=params, json=json, headers=self._get_headers(headers))
        return self._handle_response(resp)

    def patch(
        self,
        endpoint: str,
        params:   dict[str, Any] | None    = None,
        json:     dict[str, Any] | None    = None,
        headers:  dict[str, str] | None    = None,
    ) -> Any:
        url = self._build_url(endpoint)
        resp = self.client.patch(url, params=params, json=json, headers=self._get_headers(headers))
        return self._handle_response(resp)

    def delete(
        self,
        endpoint: str,
        params:   dict[str, Any] | None    = None,
        json:     dict[str, Any] | None    = None,
        headers:  dict[str, str] | None    = None,
    ) -> Any:
        url = self._build_url(endpoint)
        resp = self.client.request(
            "DELETE", url, params=params, json=json, headers=self._get_headers(headers)
        )
        return self._handle_response(resp)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "BaseClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
