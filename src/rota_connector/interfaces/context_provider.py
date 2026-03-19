"""
IContextProvider — Generic Interface for Scheduling Contexts

While the ROTA Engine uses the term "Practice" in its core data payloads 
(e.g., `PracticeContext`), conceptually this represents ANY generic 
"Scheduling Context" or "Location" where work needs to be fulfilled.

Because this Connector SDK is consumed by multiple different services, 
the exact nature of the "Context" changes depending on the domain:
- **Healthcare**: The Context is a "Clinic", "Ward", or "Hospital Practice".
- **Logistics**: The Context is a "Warehouse" or "Delivery Depot".
- **Retail**: The Context is a specific "Retail Store".

Your consuming application must implement this interface to fetch your local 
domain contexts (Depots, Wards, etc.) from your database and map their SLA 
demands (e.g. required active hours) exactly into the engine's `PracticeContext` payload.

Copyright (c) 2026 31 Green. All rights reserved.
"""

from abc import ABC, abstractmethod
from uuid import UUID
from typing import List

from rota_connector.exceptions import ContextNotFoundError, ProviderError
from rota_connector.schemas.rota import PracticeContext


class IContextProvider(ABC):
    """
    Abstract interface that consuming applications must implement to supply
    scheduling context (Practice, Location, Depot) rules to the ROTA Connector.

    ┌─────────────────────────────────────────────────────┐
    │  Your Application                                   │
    │                                                     │
    │  class PracticeProvider(IContextProvider):          │
    │      def get_practice_context(self, practice_id):   │
    │          p = Practice.objects.get(pk=practice_id)   │  ← your ORM
    │          return PracticeContext(                    │
    │              required_hours=p.shift_hours           │
    │          )                                          │
    └─────────────────────────────────────────────────────┘

    Raise ProviderError (or its subclasses) for all internal errors.
    """

    @abstractmethod
    def get_practice_context(self, practice_id: UUID) -> PracticeContext:
        """
        Fetch the exact SLA requirements (e.g. required_hours) for a context.

        The ROTA engine uses this to calculate whether a location is 
        under-staffed or over-staffed relative to its required hours.

        Args:
            practice_id: The UUID mapping to the practice in your database.

        Returns:
            PracticeContext containing SLA requirements like required_hours.

        Raises:
            ContextNotFoundError: If the practice UUID does not exist.
            ProviderError:        For any other retrieval failure.

        Example:
            def get_practice_context(self, practice_id):
                try:
                    practice = Practice.objects.get(id=practice_id)
                except Practice.DoesNotExist:
                    raise ContextNotFoundError("Practice missing.")
                return PracticeContext(required_hours=practice.hours)
        """
        ...

    @abstractmethod
    def list_practice_contexts(
        self,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[PracticeContext]:
        """
        List all SLA Practice contexts mapped from your database.

        Args:
            is_active: Filter by active/inactive status.
            skip:      Pagination offset.
            limit:     Maximum number of results.

        Returns:
            List of PracticeContext objects.

        Raises:
            ProviderError: For any retrieval failure.
        """
        ...

    @abstractmethod
    def validate_entity_in_context(self, staff_id: UUID, practice_id: UUID) -> bool:
        """
        Check whether a resource is a member of a given context.

        Used by the ROTA engine before creating assignments to prevent
        assigning staff to locations they are not authorized to work at.

        Args:
            staff_id:    UUID of the resource.
            practice_id: UUID of the context.

        Returns:
            bool: True if authorized, False otherwise.
        """
        ...

    def validate_context_exists(self, practice_id: UUID) -> bool:
        """
        Safely check if a practice context exists without fetching full details.

        Used for pre-flight validation by the ROTA service.

        Default implementation calls get_practice_context(). Override 
        for performance if a lighter check is possible.
        """
        try:
            self.get_practice_context(practice_id)
            return True
        except ContextNotFoundError:
            return False
        except ProviderError:
            return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
