# ROTA Connector SDK — Architecture

## Overview

The ROTA Connector SDK follows the same layered architecture as `auth31-connector`, extended
with a **provider interface layer** that decouples the consuming application's data model from
the ROTA Core Service API.

The key design insight: the ROTA Core Service calls staff "staff" and locations "practices".
The connector uses generic terms — **entity** (resource) and **context** — so any project can
plug in regardless of what it calls those things.

---

## Directory Structure

```
rota_connector/
├── __init__.py                      # Public API surface — exports RotaConnector + interfaces
├── client.py                        # RotaConnector — main entry point + orchestration
├── base_client.py                   # HTTP transport — auth, error mapping, connection pooling
├── configs.py                       # Base URL, version, pagination defaults
├── exceptions.py                    # Full exception hierarchy (HTTP + provider + domain)
│
├── interfaces/                      # ← Implement these in your application
│   ├── __init__.py
│   ├── resource_provider.py         # IResourceProvider — generic "staff" interface
│   └── context_provider.py          # IContextProvider  — generic "practice" interface
│
├── schemas/                         # Pydantic v2 models
│   ├── __init__.py
│   ├── common.py                    # SchedulableEntity, SchedulingContext, enums, shared models
│   ├── project.py                   # ProjectCreateSchema, ProjectOutSchema
│   └── rota.py                      # CreateAssignmentSchema, ScheduleGridRequest, etc.
│
├── api/                             # Domain API clients (one per ROTA resource group)
│   ├── __init__.py
│   ├── projects.py                  # ProjectsAPI
│   └── rota.py                      # RotaAPI (assignments, grids, staff)
│
├── ARCHITECTURE.md                  # This file
├── README.md                        # Quick start, API reference, integration guide
└── pyproject.toml                   # Packaging (Python 3.12+, httpx, pydantic v2)
```

---

## Architecture Layers

```
┌──────────────────────────────────────────────────────────────┐
│  Consuming Application  (e.g. ROTA Django project)           │
│                                                              │
│   StaffProvider(IResourceProvider)                           │
│   PracticeProvider(IContextProvider)          ← YOUR CODE    │
└──────────────────┬────────────────────────────┬─────────────┘
                   │                            │
                   ▼                            ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 4 — Client  (client.py)                               │
│  RotaConnector                                               │
│  · Wires base_client + API clients + providers               │
│  · validate_assignment_parties()  resolve_entity()           │
│  · resolve_context()  set_credentials()                      │
└──────────────────────────────┬───────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
┌───────────────────────┐ ┌────────────────────────┐
│  Layer 3 — API        │ │  Layer 3 — API         │
│  RotaAPI              │ │  ProjectsAPI           │
│                       │ │                        │
│  · practice_grid      │ │  · register_project    │
│  · staff_grid         │ │  · rotate_secret       │
│  · available_staff    │ │                        │
│  · assignments        │ │                        │
│    (create, edit,     │ │                        │
│     cancel, delete)   │ │                        │
└───────────────────────┘ └────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 2 — Base Client  (base_client.py)                     │
│  · httpx connection pool (lazy init)                         │
│  · Client ID and Secret injection                            │
│  · HTTP → typed exception mapping                            │
│  · GET / POST / PUT / PATCH / DELETE                         │
└──────────────────────────────┬───────────────────────────────┘
                               │  HTTPS
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  ROTA Core Service  (rota-backend.31g.co.uk)                 │
└──────────────────────────────────────────────────────────────┘
```

---

## The Interface Layer — Key Design Decision

### Why interfaces?

The ROTA Core Service needs to know about **staff** and **practices** when creating assignments.
Rather than forcing all projects to re-implement identical HTTP calls or share a single DB schema,
the connector defines two abstract interfaces:

| Interface | Generic name | ROTA Core name | Typical implementation |
|---|---|---|---|
| `IResourceProvider` | entity / resource | staff | Django ORM `Staff` model |
| `IContextProvider`  | context           | practice | Django ORM `Practice` model |

Any project that installs the connector implements these two interfaces against its own data source.
The connector SDK never imports from application code — the dependency arrow always points inward.

### The analogy

Think of the interfaces as **power socket standards**. The ROTA connector is an appliance with
a standard plug (`IResourceProvider`, `IContextProvider`). Each consuming project provides an
adaptor (their concrete implementation) that converts their local wiring to the standard plug.
The appliance never needs to know about the local wiring.

### Contract

```
IResourceProvider
├── get_entity(entity_id)                → SchedulableEntity   [required]
├── list_entities(context_id, ...)       → list[SchedulableEntity] [required]
├── get_entity_availability(id, range)   → EntityAvailability  [required]
├── get_entity_metadata(entity_id)       → dict                [optional, default {}]
├── list_entities_by_ids(ids)            → list[SchedulableEntity] [optional, default loops]
└── validate_entity_exists(entity_id)    → bool                [optional, default delegates]

IContextProvider
├── get_context(context_id)              → SchedulingContext   [required]
├── list_contexts(...)                   → list[SchedulingContext] [required]
├── get_context_schedule_config(id)      → ContextScheduleConfig [required]
├── get_context_entities(id, ...)        → list[SchedulableEntity] [required]
├── get_context_metadata(context_id)     → dict                [optional, default {}]
├── list_contexts_by_ids(ids)            → list[SchedulingContext] [optional, default loops]
├── validate_context_exists(id)          → bool                [optional, default delegates]
└── validate_entity_in_context(eid, cid) → bool               [optional, default iterates]
```

---

## Exception Hierarchy

```
Exception
└── RotaError                          ← catch-all for any SDK error
    ├── AuthenticationError            ← HTTP 401
    ├── AuthorizationError             ← HTTP 403
    ├── ResourceNotFoundError          ← HTTP 404
    ├── ValidationError                ← HTTP 400 / 422
    ├── ConflictError                  ← HTTP 409 (generic)
    ├── AssignmentConflictError        ← HTTP 409 + conflicting_assignment_ids
    ├── RateLimitError                 ← HTTP 429
    ├── ServerError                    ← HTTP 5xx
    └── ProviderError                  ← errors from IResourceProvider / IContextProvider
        ├── EntityNotFoundError        ← entity not found in provider
        ├── ContextNotFoundError       ← context not found in provider
        └── ProviderUnavailableError   ← underlying data source is unreachable
```

**Rule for provider implementors:** catch your ORM/DB exceptions and re-raise as
`ProviderError` or its subclasses. Never let SQLAlchemy, Django ORM, or
external API exceptions leak out of a provider method.

---

## Schema Layers

```
schemas/common.py
├── SchedulableEntity    ← normalised entity DTO (returned by IResourceProvider)
├── SchedulingContext    ← normalised context DTO (returned by IContextProvider)
├── EntityAvailability   ← availability window for an entity
├── ContextScheduleConfig← scheduling rules for a context
├── DateRangeFilter      ← shared date window
├── TimeSlot             ← a concrete time window
├── PaginatedResponse    ← generic paginated list wrapper
└── Enums: AssignmentType, AssignmentState, AssignmentStatus,
           ExceptionType, AvailabilityStatus

schemas/project.py
├── ProjectCreateSchema
└── ProjectOutSchema

schemas/rota.py
├── CreateAssignmentSchema
├── PracticeGridRequestSchema / StaffGridOut
├── AvailableStaffRequestSchema
└── EditOccurrenceSchema / EditFollowingSchema / EditAllSchema
```

---

## Data Flow

### Creating an Assignment (with providers)

```
Application Code
    │
    ├── connector.validate_assignment_parties(entity_id, context_id)
    │       │
    │       ├── resource_provider.get_entity(entity_id)      ← your DB / ORM
    │       ├── context_provider.get_context(context_id)     ← your DB / ORM
    │       └── context_provider.validate_entity_in_context(...)
    │
    └── connector.rota.create_assignment(CreateAssignmentSchema(...))
            │
            └── BaseClient.post("/api/v1/rota/assignments/")
                    │
                    └── ROTA Core Service  →  AssignmentOut (response)
```

### Fetching the Practice Grid

```
connector.rota.practice_grid(
    PracticeGridRequestSchema(week_start=..., role_id=...)
)
    │
    └── BaseClient.post("/api/v1/rota/grid/practice/")
            │
            └── ROTA Core Service  →  PracticeGridOut
                    (list of days with allocation status)
```

---

## Design Principles

### 1. Domain-agnostic naming
The SDK uses `entity` / `context` throughout. "Staff" and "practice" are ROTA Core
internals, not SDK concepts. This allows the connector to be used in any scheduling
domain.

### 2. Providers are optional
`RotaConnector` works without providers for pure API use. Providers unlock higher-level
methods (`validate_assignment_parties`, `resolve_entity`, `resolve_context`).

### 3. Separation of concerns
- `BaseClient`   → HTTP only
- `*API` classes → endpoint mapping + parameter building
- `schemas/`     → data contracts
- `interfaces/`  → application integration contracts
- `RotaConnector` → orchestration only

### 4. Fail loudly with typed exceptions
Every error path raises a specific typed exception from the hierarchy.
Consumers can catch `RotaError` for everything or the specific subclass for precise handling.
