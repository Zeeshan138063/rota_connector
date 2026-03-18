# ROTA Connector SDK

Python 3.12+ connector for the **ROTA Core Service** — Resource Optimisation & Time Allocation engine.

---

## Installation

```bash
pip install rota-connector
```

**Requirements:** Python 3.12+, `httpx>=0.27`, `pydantic>=2.10`

---

## Quick Start

### Minimal — API calls only

```python
from rota_connector import RotaConnector

connector = RotaConnector()
connector.set_credentials("<client_id>", "<client_secret>")

# List available staff for a practice
from rota_connector.schemas.rota import AvailableStaffRequestSchema
from datetime import date

available = connector.rota.available_staff(
    practice_id=practice_id,
    target_date=date(2026, 4, 1),
    role_id=role_id,
    payload=AvailableStaffRequestSchema(staff_contexts=[])
)

# Get the schedule grid
from rota_connector.schemas.rota import PracticeGridRequestSchema

grid = connector.rota.practice_grid(
    PracticeGridRequestSchema(
        week_start=date(2026, 4, 6),
        role_id=role_id,
        practice_contexts={}
    )
)
```

### Context manager

```python
with RotaConnector() as connector:
    connector.set_credentials(client_id, client_secret)
    connector.rota.create_assignment(payload)
```

---

## Full Integration — Provider Interfaces

For projects that need validated, domain-aware scheduling, implement the two provider interfaces.
These bridge your application's data model to the ROTA connector.

### Step 1 — Implement IResourceProvider

`IResourceProvider` maps your **staff / employee** model to the generic `SchedulableEntity` DTO.

```python
from uuid import UUID
from rota_connector import IResourceProvider
from rota_connector.schemas import SchedulableEntity, EntityAvailability, DateRangeFilter, AvailabilityStatus
from rota_connector.exceptions import EntityNotFoundError, ProviderError

# Example using a Django ORM Staff model
class StaffProvider(IResourceProvider):

    def get_entity(self, entity_id: UUID) -> SchedulableEntity:
        try:
            staff = Staff.objects.get(pk=entity_id)
        except Staff.DoesNotExist:
            raise EntityNotFoundError(f"Staff {entity_id} not found")
        return SchedulableEntity(
            entity_id=staff.id,
            display_name=staff.full_name,
            entity_type=staff.role,           # "nurse", "doctor", etc.
            context_ids=[p.id for p in staff.practices.all()],
            is_active=staff.is_active,
        )

    def list_entities(
        self,
        context_id=None,
        is_active=True,
        entity_type=None,
        skip=0,
        limit=100,
    ) -> list[SchedulableEntity]:
        qs = Staff.objects.filter(is_active=is_active)
        if context_id:
            qs = qs.filter(practices__id=context_id)
        if entity_type:
            qs = qs.filter(role=entity_type)
        return [self._map(s) for s in qs[skip : skip + limit]]

    def get_entity_availability(
        self,
        entity_id: UUID,
        date_range: DateRangeFilter,
    ) -> EntityAvailability:
        leaves = Leave.objects.filter(
            staff_id=entity_id,
            start_date__lte=date_range.end_date,
            end_date__gte=date_range.start_date,
        )
        status = AvailabilityStatus.UNAVAILABLE if leaves.exists() else AvailabilityStatus.AVAILABLE
        return EntityAvailability(
            entity_id=entity_id,
            date_range=date_range,
            status=status,
            slots=[],
        )

    def _map(self, staff) -> SchedulableEntity:
        return SchedulableEntity(
            entity_id=staff.id,
            display_name=staff.full_name,
            entity_type=staff.role,
            is_active=staff.is_active,
        )
```

### Step 2 — Implement IContextProvider

`IContextProvider` maps your **practice / location** model to the generic `SchedulingContext` DTO.

```python
from uuid import UUID
from rota_connector import IContextProvider
from rota_connector.schemas import (
    SchedulingContext, ContextScheduleConfig, SchedulableEntity,
    AssignmentType,
)
from rota_connector.exceptions import ContextNotFoundError

class PracticeProvider(IContextProvider):

    def get_context(self, context_id: UUID) -> SchedulingContext:
        try:
            practice = Practice.objects.get(pk=context_id)
        except Practice.DoesNotExist:
            raise ContextNotFoundError(f"Practice {context_id} not found")
        return SchedulingContext(
            context_id=practice.id,
            display_name=practice.name,
            context_type="practice",
            is_active=practice.is_active,
            timezone=practice.timezone,
        )

    def list_contexts(self, is_active=True, context_type=None, skip=0, limit=100):
        qs = Practice.objects.filter(is_active=is_active)
        return [self._map(p) for p in qs[skip : skip + limit]]

    def get_context_schedule_config(self, context_id: UUID) -> ContextScheduleConfig:
        practice = Practice.objects.select_related("config").get(pk=context_id)
        return ContextScheduleConfig(
            context_id=context_id,
            default_shift_hours=practice.config.shift_hours,
            allowed_assignment_types=[AssignmentType.SINGLE, AssignmentType.RECURRING],
            requires_confirmation=practice.config.requires_staff_confirmation,
            timezone=practice.timezone,
        )

    def get_context_entities(self, context_id, is_active=True, skip=0, limit=100):
        memberships = PracticeMembership.objects.filter(
            practice_id=context_id,
            staff__is_active=is_active,
        ).select_related("staff")[skip : skip + limit]
        return [
            SchedulableEntity(
                entity_id=m.staff.id,
                display_name=m.staff.full_name,
                entity_type=m.staff.role,
            )
            for m in memberships
        ]

    def _map(self, practice) -> SchedulingContext:
        return SchedulingContext(
            context_id=practice.id,
            display_name=practice.name,
            context_type="practice",
            is_active=practice.is_active,
            timezone=practice.timezone,
        )
```

### Step 3 — Wire everything together

```python
from rota_connector import RotaConnector

connector = RotaConnector(
    resource_provider=StaffProvider(),
    context_provider=PracticeProvider(),
)
connector.set_credentials(client_id, client_secret)

# Pre-flight validation before creating an assignment
is_valid = connector.validate_assignment_parties(
    entity_id=staff_id,
    context_id=practice_id,
)

if is_valid:
    from rota_connector.schemas.rota import CreateAssignmentSchema
    from rota_connector.schemas.common import AssignmentType
    from datetime import time, date

    assignment = connector.rota.create_assignment(
        CreateAssignmentSchema(
            staff_id=staff_id,
            practice_id=practice_id,
            role_id=role_id,
            assignment_type=AssignmentType.ONCE,
            date=date(2026, 4, 7),
            start_time=time(9, 0),
            end_time=time(17, 0),
            staff_context=staff_context_payload,
            practice_context=practice_context_payload,
        )
    )
```

---

## API Reference

### RotaConnector

```python
RotaConnector(
    base_url="https://rota-backend.31g.co.uk",  # override for local dev
    version="v1",
    timeout=30.0,
    verify_ssl=True,
    resource_provider=None,   # IResourceProvider implementation
    context_provider=None,    # IContextProvider implementation
)
```

| Method | Description |
|---|---|
| `set_credentials(client_id, secret)` | Set Client ID and Secret for all requests |
| `clear_credentials()` | Remove the current credentials |
| `set_resource_provider(p)` | Attach / replace resource provider at runtime |
| `set_context_provider(p)` | Attach / replace context provider at runtime |
| `resolve_entity(entity_id)` | Fetch entity via resource provider |
| `resolve_context(context_id)` | Fetch context via context provider |
| `validate_assignment_parties(entity_id, context_id)` | Check entity + context are valid and related |
| `close()` | Release HTTP connections |

---

### connector.rota (RotaAPI)

| Method | Description |
|---|---|
| `practice_grid(payload: PracticeGridRequestSchema)` | Get Practice Grid |
| `staff_grid(week_start, role_id, ...)` | Get Staff Grid |
| `available_staff(practice_id, target_date, role_id, payload)` | Get Available Staff |
| `last_end_date(practice_id, role_id)` | Get Last End Date |
| `create_assignment(payload: CreateAssignmentSchema)` | Create single or recurring assignment |
| `edit_occurrence(assignment_id, payload)` | Edit single occurrence |
| `edit_following(assignment_id, payload)` | Edit this and following occurrences |
| `edit_all(assignment_id, payload)` | Edit all occurrences |
| `cancel_occurrence(assignment_id, payload)` | Cancel a single occurrence |
| `delete_assignment(assignment_id)` | Delete assignment |

---

## Exception Handling

```python
from rota_connector.exceptions import (
    RotaError,              # catch-all
    AuthenticationError,    # 401 — credentials invalid or missing
    AuthorizationError,     # 403 — insufficient permissions
    ResourceNotFoundError,  # 404
    ValidationError,        # 400 / 422
    AssignmentConflictError,# 409 — scheduling conflict (has .conflicting_assignment_ids)
    RateLimitError,         # 429
    ServerError,            # 5xx
    EntityNotFoundError,    # provider: entity not found
    ContextNotFoundError,   # provider: context not found
    ProviderError,          # provider: any other failure
)

try:
    connector.assignments.create(payload)
except AssignmentConflictError as e:
    print(f"Conflicts with: {e.conflicting_assignment_ids}")
except AuthenticationError:
    # re-authenticate and retry
    ...
except RotaError as e:
    print(f"ROTA error {e.status_code}: {e.message}")
```

---

## Provider Error Contract

Implementors of `IResourceProvider` and `IContextProvider` **must** catch all
internal exceptions and re-raise as `ProviderError` or its subclasses:

```python
# ✅ Correct
def get_entity(self, entity_id):
    try:
        return Staff.objects.get(pk=entity_id)
    except Staff.DoesNotExist:
        raise EntityNotFoundError(f"Staff {entity_id} not found")
    except DatabaseError as e:
        raise ProviderUnavailableError(f"DB unavailable: {e}")

# ❌ Wrong — leaks ORM exception to the connector
def get_entity(self, entity_id):
    return Staff.objects.get(pk=entity_id)  # DoesNotExist leaks!
```

---

## Copyright

Copyright (c) 2026 31 Green. All rights reserved.
This software is proprietary and confidential. Unauthorised copying or distribution is strictly prohibited.
