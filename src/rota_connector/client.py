"""
Main ROTA Connector SDK client

Copyright (c) 2026 31 Green. All rights reserved.
This software is proprietary and confidential.
Unauthorized copying or distribution is strictly prohibited.
"""

from typing import Any

from rota_connector.api.projects import ProjectsAPI
from rota_connector.api.rota import RotaAPI
from rota_connector.base_client import BaseClient
from rota_connector.configs import ROTA_BASE_URL, ROTA_DEFAULT_VERSION
from rota_connector.interfaces.context_provider import IContextProvider
from rota_connector.interfaces.resource_provider import IResourceProvider


class RotaConnector:
    """
    Main entry point for the ROTA Connector SDK.

    Wires together:
    - HTTP transport (BaseClient)
    - Domain API clients (RotaAPI, ProjectsAPI)
    - Provider interfaces (IResourceProvider, IContextProvider)

    Usage — minimal (API calls only):
    ──────────────────────────────────
        connector = RotaConnector()
        connector.set_credentials("<client_id>", "<client_secret>")
        assignments = connector.rota.last_end_date(practice_id, role_id)
    Usage — with providers (recommended for full integration):
    ──────────────────────────────────────────────────────────
        class MyStaffProvider(IResourceProvider):
            def get_entity(self, entity_id): ...
            def list_entities(self, ...): ...
            def get_entity_availability(self, ...): ...

        class MyPracticeProvider(IContextProvider):
            def get_context(self, context_id): ...
            def list_contexts(self, ...): ...
            def get_context_schedule_config(self, ...): ...
            def get_context_entities(self, ...): ...

        connector = RotaConnector(
            resource_provider=MyStaffProvider(),
            context_provider=MyPracticeProvider(),
        )

    Usage — context manager:
    ────────────────────────
        with RotaConnector() as connector:
            connector.set_credentials(client_id, client_secret)
            connector.rota.create_assignment(payload)
    """

    def __init__(
        self,
        base_url:          str                    = ROTA_BASE_URL,
        version:           str                    = ROTA_DEFAULT_VERSION,
        timeout:           float                  = 30.0,
        verify_ssl:        bool                   = True,
        resource_provider: IResourceProvider | None = None,
        context_provider:  IContextProvider | None  = None,
    ):
        """
        Initialise the ROTA Connector.

        Args:
            base_url:          Base URL for the ROTA Core Service.
            version:           API version string (default "v1").
            timeout:           HTTP request timeout in seconds.
            verify_ssl:        Whether to verify TLS certificates.
            resource_provider: IResourceProvider implementation from the
                               consuming application (maps to "staff" data).
            context_provider:  IContextProvider implementation from the
                               consuming application (maps to "practice" data).
        """
        self._base_client = BaseClient(
            base_url=base_url,
            timeout=timeout,
            verify_ssl=verify_ssl,
        )
        self._version = version

        # ── Provider interfaces ───────────────────────────────────────────────
        # These are optional — the connector works without them for pure
        # API-call use cases. With them, higher-level helper methods
        # (e.g. validate before create, resolve names) become available.
        self.resource_provider: IResourceProvider | None = resource_provider
        self.context_provider:  IContextProvider  | None = context_provider

        # ── API clients ───────────────────────────────────────────────────────
        self.rota      = RotaAPI(self._base_client, version)
        self.projects  = ProjectsAPI(self._base_client, version)

    # ── Auth ──────────────────────────────────────────────────────────────────

    def set_credentials(self, client_id: str, client_secret: str) -> None:
        """Set the Client ID and Secret for all subsequent API requests."""
        self._base_client.set_credentials(client_id, client_secret)

    def clear_credentials(self) -> None:
        """Remove the current credentials."""
        self._base_client.clear_credentials()

    def health(self) -> "Any":
        """
        Check the health and connectivity of the upstream ROTA Core Service.
        """
        return self._base_client.get("/api/v1/health")

    # ── Provider wiring ───────────────────────────────────────────────────────

    def set_resource_provider(self, provider: IResourceProvider) -> None:
        """
        Attach or replace the IResourceProvider at runtime.

        Useful when the provider depends on the current request context
        (e.g. a Django request-scoped queryset).
        """
        self.resource_provider = provider

    def set_context_provider(self, provider: IContextProvider) -> None:
        """
        Attach or replace the IContextProvider at runtime.
        """
        self.context_provider = provider

    # ── Higher-level helpers (require providers) ──────────────────────────────

    def resolve_entity(self, entity_id: "Any") -> "Any":
        """
        Fetch entity data from the resource provider.

        Raises:
            RuntimeError:        If no resource_provider is configured.
            EntityNotFoundError: If the entity does not exist.
        """
        if self.resource_provider is None:
            raise RuntimeError(
                "resolve_entity() requires a resource_provider. "
                "Pass one to RotaConnector() or call set_resource_provider()."
            )
        return self.resource_provider.get_entity(entity_id)

    def resolve_context(self, context_id: "Any") -> "Any":
        """
        Fetch context data from the context provider.

        Raises:
            RuntimeError:         If no context_provider is configured.
            ContextNotFoundError: If the context does not exist.
        """
        if self.context_provider is None:
            raise RuntimeError(
                "resolve_context() requires a context_provider. "
                "Pass one to RotaConnector() or call set_context_provider()."
            )
        return self.context_provider.get_context(context_id)

    def validate_assignment_parties(
        self,
        entity_id:  "Any",
        context_id: "Any",
    ) -> bool:
        """
        Validate that both the entity and context exist, and that the entity
        is a member of the context — before creating an assignment.

        Requires both providers to be configured.

        Returns:
            True if the assignment parties are valid.

        Raises:
            RuntimeError:         If providers are not configured.
            EntityNotFoundError:  If the entity does not exist.
            ContextNotFoundError: If the context does not exist.
        """
        if self.resource_provider is None or self.context_provider is None:
            raise RuntimeError(
                "validate_assignment_parties() requires both resource_provider "
                "and context_provider to be configured."
            )
        self.resource_provider.get_entity(entity_id)     # raises if not found
        self.context_provider.get_context(context_id)    # raises if not found
        return self.context_provider.validate_entity_in_context(entity_id, context_id)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        self._base_client.close()

    def __enter__(self) -> "RotaConnector":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        has_resource = self.resource_provider is not None
        has_context  = self.context_provider is not None
        return (
            f"RotaConnector("
            f"version={self._version!r}, "
            f"resource_provider={has_resource}, "
            f"context_provider={has_context})"
        )
