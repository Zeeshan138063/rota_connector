"""
IContextProvider — Generic interface for scheduling context data

Any project consuming the ROTA Connector must implement this interface
to bridge its own context/tenant model to the ROTA engine.

"Context" is the generic term for what ROTA Core calls "practice".
In a GP surgery this is a practice/clinic. In logistics it is a depot.
The connector stays domain-agnostic by always talking to IContextProvider.

Copyright (c) 2026 31 Green. All rights reserved.
This software is proprietary and confidential.
Unauthorized copying or distribution is strictly prohibited.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from rota_connector.exceptions import ContextNotFoundError, ProviderError
from rota_connector.schemas.common import (
    ContextScheduleConfig,
    SchedulableEntity,
    SchedulingContext,
)


class IContextProvider(ABC):
    """
    Abstract interface that consuming applications must implement to supply
    scheduling context (practice / location) data to the ROTA Connector.

    ┌──────────────────────────────────────────────────────────┐
    │  Your Application                                        │
    │                                                          │
    │  class PracticeProvider(IContextProvider):               │
    │      def get_context(self, context_id):                  │
    │          p = Practice.objects.get(pk=context_id)         │  ← your ORM
    │          return SchedulingContext(                       │
    │              context_id=p.id,                            │
    │              display_name=p.name,                        │
    │              context_type="practice",                    │
    │              timezone=p.timezone,                        │
    │          )                                               │
    └──────────────────────────────────────────────────────────┘

    Raise ProviderError (or its subclasses) for all internal errors.

    Why separate from IResourceProvider?
    ────────────────────────────────────
    Resources (staff) and Contexts (practices) have different lifetimes,
    permissions, and data owners. Keeping them as two interfaces lets
    projects wire different data sources for each — e.g. staff from LDAP,
    practices from the local Postgres database.
    """

    # ── Required methods ─────────────────────────────────────────────────────

    @abstractmethod
    def get_context(self, context_id: UUID) -> SchedulingContext:
        """
        Fetch a single scheduling context by its ID.

        Args:
            context_id: The context's UUID as stored in your application.

        Returns:
            SchedulingContext populated from your data source.

        Raises:
            ContextNotFoundError: If no context exists with this ID.
            ProviderError:        For any other retrieval failure.

        Example:
            def get_context(self, context_id: UUID) -> SchedulingContext:
                try:
                    practice = Practice.objects.get(pk=context_id)
                except Practice.DoesNotExist:
                    raise ContextNotFoundError(f"Practice {context_id} not found")
                return self._to_scheduling_context(practice)
        """
        ...

    @abstractmethod
    def list_contexts(
        self,
        is_active:    bool        = True,
        context_type: str | None  = None,
        skip:  int = 0,
        limit: int = 100,
    ) -> list[SchedulingContext]:
        """
        List scheduling contexts available to this connector instance.

        Args:
            is_active:    Filter by active/inactive status.
            context_type: Filter by context type (e.g. "practice", "ward").
            skip:         Pagination offset.
            limit:        Maximum number of results.

        Returns:
            List of SchedulingContext objects.

        Raises:
            ProviderError: For any retrieval failure.

        Example:
            def list_contexts(self, is_active=True, context_type=None, ...):
                qs = Practice.objects.filter(is_active=is_active)
                if context_type:
                    qs = qs.filter(type=context_type)
                return [self._to_scheduling_context(p) for p in qs[skip:skip+limit]]
        """
        ...

    @abstractmethod
    def get_context_schedule_config(self, context_id: UUID) -> ContextScheduleConfig:
        """
        Return the scheduling configuration for a context.

        The ROTA engine uses this to determine:
        - Default shift duration
        - Allowed assignment types (single vs recurring)
        - Whether assignments require confirmation
        - Timezone for date calculations

        Args:
            context_id: The context's UUID.

        Returns:
            ContextScheduleConfig with the context's scheduling rules.

        Raises:
            ContextNotFoundError: If the context does not exist.
            ProviderError:        For any other retrieval failure.

        Example:
            def get_context_schedule_config(self, context_id):
                practice = Practice.objects.select_related("schedule_config").get(pk=context_id)
                cfg = practice.schedule_config
                return ContextScheduleConfig(
                    context_id=context_id,
                    default_shift_hours=cfg.shift_hours,
                    requires_confirmation=cfg.requires_confirmation,
                    timezone=practice.timezone,
                )
        """
        ...

    @abstractmethod
    def get_context_entities(
        self,
        context_id: UUID,
        is_active:  bool = True,
        skip:  int = 0,
        limit: int = 100,
    ) -> list[SchedulableEntity]:
        """
        Return all entities (resources) belonging to a context.

        This is the context-first view — "give me all staff at practice X".
        The resource-first equivalent is IResourceProvider.list_entities(context_id=...).

        Args:
            context_id: The context's UUID.
            is_active:  Filter by active/inactive status.
            skip:       Pagination offset.
            limit:      Maximum results.

        Returns:
            List of SchedulableEntity objects.

        Raises:
            ContextNotFoundError: If the context does not exist.
            ProviderError:        For any other retrieval failure.

        Example:
            def get_context_entities(self, context_id, is_active=True, ...):
                memberships = PracticeMembership.objects.filter(
                    practice_id=context_id,
                    staff__is_active=is_active,
                ).select_related("staff")
                return [self._to_schedulable_entity(m.staff) for m in memberships]
        """
        ...

    # ── Optional methods (sensible defaults provided) ─────────────────────────

    def get_context_metadata(self, context_id: UUID) -> dict:
        """
        Return arbitrary app-specific metadata for a context.

        Override to expose extra fields (e.g. address, CCG code, capacity)
        to the ROTA engine or UI layer.

        Default returns an empty dict.
        """
        return {}

    def list_contexts_by_ids(self, context_ids: list[UUID]) -> list[SchedulingContext]:
        """
        Batch-fetch contexts by a list of IDs.

        Default calls get_context() in a loop.
        Override with a bulk query for performance.
        """
        results: list[SchedulingContext] = []
        for cid in context_ids:
            results.append(self.get_context(cid))
        return results

    def validate_context_exists(self, context_id: UUID) -> bool:
        """
        Check if a context exists without fetching full details.

        Default delegates to get_context(). Override for a lighter check.
        """
        try:
            self.get_context(context_id)
            return True
        except ContextNotFoundError:
            return False
        except ProviderError:
            return False

    def validate_entity_in_context(self, entity_id: UUID, context_id: UUID) -> bool:
        """
        Check whether an entity is a member of a given context.

        Used by the ROTA engine before creating assignments to prevent
        assigning staff to practices they don't belong to.

        Default iterates get_context_entities() — override with a direct
        membership check for better performance.
        """
        try:
            entities = self.get_context_entities(context_id)
            return any(e.entity_id == entity_id for e in entities)
        except ProviderError:
            return False

    # ── Dunder helpers ────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
