"""
IResourceProvider — Generic Interface for Schedulable Resources

While the ROTA Engine uses the term "Staff" in its core data payloads 
(e.g., `StaffContextEnriched`), conceptually this represents ANY generic 
"Schedulable Resource" or "Entity" that has working capacity.

Because this Connector SDK is consumed by multiple different services, 
the exact nature of the "Resource" changes depending on the domain:
- **Healthcare**: The Resource is a "Nurse", "Doctor", or "Pharmacist".
- **Logistics**: The Resource is a "Delivery Driver" or a "Vehicle".
- **Retail**: The Resource is a "Store Clerk".

Your consuming application must implement this interface to fetch your local 
domain entities (Drivers, Nurses, etc.) from your database and map their 
working capacity directly into the engine's strict `StaffContextEnriched` payload.

Copyright (c) 2026 31 Green. All rights reserved.
"""

from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional

from rota_connector.exceptions import EntityNotFoundError, ProviderError
from rota_connector.schemas.common import DateRangeFilter
from rota_connector.schemas.rota import StaffContextEnriched


class IResourceProvider(ABC):
    """
    Abstract interface that consuming applications must implement to supply
    schedulable resource data (Staff, Drivers, etc.) to the ROTA Connector.

    ┌─────────────────────────────────────────────────────┐
    │  Your Application (e.g. Django)                     │
    │                                                     │
    │  class StaffProvider(IResourceProvider):            │
    │      def get_staff_context(self, staff_id):         │
    │          u = User.objects.get(pk=staff_id)          │  ← your ORM
    │          return StaffContextEnriched(               │
    │              staff_id=u.id,                         │
    │              weekly_capacity=u.hours,               │
    │              ...                                    │
    │          )                                          │
    └─────────────────────────────────────────────────────┘

    Raise ProviderError (or its subclasses) for all internal errors so the
    connector can handle them uniformly. Never let ORM/DB exceptions bubble up.
    """

    @abstractmethod
    def get_staff_context(
        self, staff_id: UUID, date_range: Optional[DateRangeFilter] = None
    ) -> StaffContextEnriched:
        """
        Fetch the explicit working capacity, active dates, and weekly day slots 
        for a single schedulable resource.

        The ROTA engine uses this to calculate real-time availability and 
        validate whether an assignment fits within a person's contract.

        Args:
            staff_id: The UUID mapping to the resource in your database.
            date_range: Optional filter window for dynamic slots (e.g. if 
                        availability changes per week).

        Returns:
            StaffContextEnriched containing weekly_capacity and day_slots.

        Raises:
            EntityNotFoundError: If the resource UUID does not exist.
            ProviderError:       For any other retrieval failure (DB down, etc).

        Example:
            def get_staff_context(self, staff_id, date_range=None):
                try:
                    user = User.objects.get(id=staff_id)
                except User.DoesNotExist:
                    raise EntityNotFoundError(f"User {staff_id} not found")
                return StaffContextEnriched(...)
        """
        ...

    @abstractmethod
    def list_staff_contexts(
        self,
        practice_id: Optional[UUID] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[StaffContextEnriched]:
        """
        List working contexts for multiple resources, optionally filtered by context.

        Args:
            practice_id: If provided, filter strictly to resources who operate 
                         at this specific practice/location.
            is_active:   Filter by active/inactive status.
            skip:        Pagination offset.
            limit:       Maximum number of results to return.

        Returns:
            List of StaffContextEnriched objects.

        Raises:
            ProviderError: For any retrieval failure.
        """
        ...

    def validate_entity_exists(self, staff_id: UUID) -> bool:
        """
        Safely check if a resource exists without fetching full details.

        Used by the ROTA service to perform pre-flight checks before 
        attempting complex scheduling operations.

        Default implementation calls get_staff_context(). Override for 
        performance if a lighter check is possible.
        """
        try:
            self.get_staff_context(staff_id)
            return True
        except EntityNotFoundError:
            return False
        except ProviderError:
            return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
