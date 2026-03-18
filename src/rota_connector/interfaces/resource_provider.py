"""
IResourceProvider — Generic interface for schedulable entity data

Any project consuming the ROTA Connector must implement this interface
to bridge its own data model (Django ORM, SQLAlchemy, external API, etc.)
to the ROTA engine.

"Resource" is the generic term for what ROTA Core calls "staff".
In a GP surgery this is a nurse. In a warehouse it is a worker.
The connector stays domain-agnostic by always talking to IResourceProvider.

Copyright (c) 2026 31 Green. All rights reserved.
This software is proprietary and confidential.
Unauthorized copying or distribution is strictly prohibited.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from rota_connector.exceptions import EntityNotFoundError, ProviderError
from rota_connector.schemas.common import (
    DateRangeFilter,
    EntityAvailability,
    SchedulableEntity,
)


class IResourceProvider(ABC):
    """
    Abstract interface that consuming applications must implement to supply
    schedulable entity (staff / resource) data to the ROTA Connector.

    ┌─────────────────────────────────────────────────────┐
    │  Your Application                                   │
    │                                                     │
    │  class StaffProvider(IResourceProvider):            │
    │      def get_entity(self, entity_id):               │
    │          staff = Staff.objects.get(pk=entity_id)    │  ← your ORM
    │          return SchedulableEntity(                  │
    │              entity_id=staff.id,                    │
    │              display_name=staff.full_name,          │
    │              entity_type="nurse",                   │
    │          )                                          │
    └─────────────────────────────────────────────────────┘

    Raise ProviderError (or its subclasses) for all internal errors so the
    connector can handle them uniformly. Never let ORM/DB exceptions bubble up.

    Example subclasses for different stack layers:
    - Django:      StaffDjangoProvider(IResourceProvider)
    - SQLAlchemy:  StaffSQLAlchemyProvider(IResourceProvider)
    - REST source: StaffAPIProvider(IResourceProvider)
    """

    # ── Required methods ─────────────────────────────────────────────────────

    @abstractmethod
    def get_entity(self, entity_id: UUID) -> SchedulableEntity:
        """
        Fetch a single schedulable entity by its ID.

        Args:
            entity_id: The entity's UUID as stored in your application.

        Returns:
            SchedulableEntity populated from your data source.

        Raises:
            EntityNotFoundError: If no entity exists with this ID.
            ProviderError:       For any other retrieval failure.

        Example:
            def get_entity(self, entity_id: UUID) -> SchedulableEntity:
                try:
                    staff = Staff.objects.get(pk=entity_id)
                except Staff.DoesNotExist:
                    raise EntityNotFoundError(f"Staff {entity_id} not found")
                return self._to_schedulable_entity(staff)
        """
        ...

    @abstractmethod
    def list_entities(
        self,
        context_id: UUID | None = None,
        is_active:  bool        = True,
        entity_type: str | None = None,
        skip:  int = 0,
        limit: int = 100,
    ) -> list[SchedulableEntity]:
        """
        List schedulable entities, optionally filtered by context membership.

        Args:
            context_id:  If provided, return only entities belonging to this context
                         (e.g. all nurses at a specific practice).
            is_active:   Filter by active/inactive status.
            entity_type: Filter by entity type (e.g. "nurse", "doctor").
            skip:        Pagination offset.
            limit:       Maximum number of results.

        Returns:
            List of SchedulableEntity objects.

        Raises:
            ProviderError: For any retrieval failure.

        Example:
            def list_entities(self, context_id=None, is_active=True, ...):
                qs = Staff.objects.filter(is_active=is_active)
                if context_id:
                    qs = qs.filter(practices__id=context_id)
                return [self._to_schedulable_entity(s) for s in qs[skip:skip+limit]]
        """
        ...

    @abstractmethod
    def get_entity_availability(
        self,
        entity_id:  UUID,
        date_range: DateRangeFilter,
    ) -> EntityAvailability:
        """
        Return the availability of an entity over a date range.

        The ROTA engine calls this before creating assignments to check
        whether the entity is free, unavailable (leave, sickness), or partial.

        Args:
            entity_id:  The entity's UUID.
            date_range: The date window to check.

        Returns:
            EntityAvailability describing available/unavailable slots.

        Raises:
            EntityNotFoundError: If the entity does not exist.
            ProviderError:       For any other retrieval failure.

        Example:
            def get_entity_availability(self, entity_id, date_range):
                leaves = Leave.objects.filter(
                    staff_id=entity_id,
                    start_date__lte=date_range.end_date,
                    end_date__gte=date_range.start_date,
                )
                # build and return EntityAvailability from leave records
        """
        ...

    # ── Optional methods (provide sensible defaults) ──────────────────────────

    def get_entity_metadata(self, entity_id: UUID) -> dict:
        """
        Return arbitrary app-specific metadata for an entity.

        Override this to expose extra fields (e.g. job title, band grade,
        qualifications) to the ROTA engine's auto-scheduling logic.

        Default returns an empty dict (no metadata enrichment).
        """
        return {}

    def list_entities_by_ids(self, entity_ids: list[UUID]) -> list[SchedulableEntity]:
        """
        Batch-fetch entities by a list of IDs.

        Default implementation calls get_entity() in a loop.
        Override with a bulk query for performance.

        Raises:
            EntityNotFoundError: If any entity is not found.
            ProviderError:       For any retrieval failure.
        """
        results: list[SchedulableEntity] = []
        for eid in entity_ids:
            results.append(self.get_entity(eid))
        return results

    def validate_entity_exists(self, entity_id: UUID) -> bool:
        """
        Check if an entity exists without fetching full details.

        Default delegates to get_entity(). Override for a lighter exists-check.
        """
        try:
            self.get_entity(entity_id)
            return True
        except EntityNotFoundError:
            return False
        except ProviderError:
            return False

    # ── Dunder helpers ────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
