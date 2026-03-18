"""
ROTA Connector SDK

Python 3.12+ connector for the ROTA Core Service (Resource Optimisation
& Time Allocation engine).

Quick start
-----------
Minimal (API calls only):

    from rota_connector import RotaConnector

    connector = RotaConnector()
    connector.set_credentials("<client_id>", "<client_secret>")
    assignments = connector.assignments.list_by_context(practice_id)

With provider interfaces (full integration):

    from rota_connector import RotaConnector, IResourceProvider, IContextProvider
    from rota_connector.schemas import SchedulableEntity, SchedulingContext

    class StaffProvider(IResourceProvider):
        def get_entity(self, entity_id): ...
        def list_entities(self, ...): ...
        def get_entity_availability(self, ...): ...

    class PracticeProvider(IContextProvider):
        def get_context(self, context_id): ...
        def list_contexts(self, ...): ...
        def get_context_schedule_config(self, ...): ...
        def get_context_entities(self, ...): ...

    connector = RotaConnector(
        resource_provider=StaffProvider(),
        context_provider=PracticeProvider(),
    )

Copyright (c) 2026 31 Green. All rights reserved.
This software is proprietary and confidential.
Unauthorized copying or distribution is strictly prohibited.
"""

from rota_connector.client import RotaConnector
from rota_connector.interfaces.context_provider import IContextProvider
from rota_connector.interfaces.resource_provider import IResourceProvider
from rota_connector.exceptions import (
    AssignmentConflictError,
    AuthenticationError,
    AuthorizationError,
    ContextNotFoundError,
    EntityNotFoundError,
    ProviderError,
    ProviderUnavailableError,
    RateLimitError,
    RecurrenceError,
    ResourceNotFoundError,
    RotaError,
    ServerError,
    ValidationError,
)

__version__ = "1.0.0"

__all__ = [
    # Main client
    "RotaConnector",
    # Interfaces — implement these in your application
    "IResourceProvider",
    "IContextProvider",
    # Exceptions
    "RotaError",
    "AuthenticationError",
    "AuthorizationError",
    "ResourceNotFoundError",
    "ValidationError",
    "ConflictError",
    "AssignmentConflictError",
    "RateLimitError",
    "ServerError",
    "ProviderError",
    "EntityNotFoundError",
    "ContextNotFoundError",
    "ProviderUnavailableError",
    "RecurrenceError",
]
