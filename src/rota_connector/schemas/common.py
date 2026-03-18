"""
Shared / common Pydantic schemas for ROTA Connector SDK

These models are used across multiple API modules and by the
interface layer as standardised data-transfer objects.

Copyright (c) 2026 31 Green. All rights reserved.
This software is proprietary and confidential.
Unauthorized copying or distribution is strictly prohibited.
"""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────────────────────

class AssignmentType(StrEnum):
    ONCE      = "once"
    RECURRING = "recurring"


class AssignmentState(StrEnum):
    DRAFT      = "draft"
    CONFIRMED  = "confirmed"
    CANCELLED  = "cancelled"
    PENDING    = "pending"


class AssignmentStatus(StrEnum):
    ACTIVE   = "active"
    INACTIVE = "inactive"


class ExceptionType(StrEnum):
    CANCELLED = "cancelled"
    MODIFIED  = "modified"
    ADDED     = "added"


class AvailabilityStatus(StrEnum):
    AVAILABLE    = "available"
    UNAVAILABLE  = "unavailable"
    PARTIAL      = "partial"


# ── Common response wrappers ──────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    """Generic paginated list wrapper returned by list endpoints."""
    items: list        = Field(default_factory=list)
    total: int         = 0
    skip:  int         = 0
    limit: int         = 100


class DateRangeFilter(BaseModel):
    """Date range used for availability and schedule queries."""
    start_date: date
    end_date:   date


class TimeSlot(BaseModel):
    """A concrete time window within a single day."""
    start_time: datetime
    end_time:   datetime


# ── Standardised entity models (used by interface layer) ─────────────────────

class SchedulableEntity(BaseModel):
    """
    Normalised representation of any schedulable resource (e.g. a staff member).

    Consumer apps return this from IResourceProvider implementations so the
    ROTA connector always works with a consistent shape regardless of how the
    host application stores its staff/employee data.
    """
    entity_id:    UUID
    display_name: str
    entity_type:  str                        # e.g. "nurse", "doctor", "employee"
    context_ids:  list[UUID] = Field(default_factory=list)  # contexts this entity belongs to
    is_active:    bool       = True
    metadata:     dict       = Field(default_factory=dict)  # app-specific extra fields


class SchedulingContext(BaseModel):
    """
    Normalised representation of any scheduling context (e.g. a practice / location).

    Consumer apps return this from IContextProvider implementations.
    """
    context_id:   UUID
    display_name: str
    context_type: str                        # e.g. "practice", "department", "ward"
    is_active:    bool = True
    timezone:     str  = "UTC"
    metadata:     dict = Field(default_factory=dict)


class EntityAvailability(BaseModel):
    """Availability window for a SchedulableEntity over a date range."""
    entity_id:   UUID
    date_range:  DateRangeFilter
    status:      AvailabilityStatus
    slots:       list[TimeSlot]  = Field(default_factory=list)
    notes:       str | None      = None


class ContextScheduleConfig(BaseModel):
    """
    Scheduling configuration for a SchedulingContext.

    Consumer apps return this from IContextProvider so the ROTA engine
    can apply the correct rules when generating assignments.
    """
    context_id:          UUID
    default_shift_hours: float        = 8.0
    allowed_assignment_types: list[AssignmentType] = Field(
        default_factory=lambda: list(AssignmentType)
    )
    requires_confirmation: bool       = False
    timezone:              str        = "UTC"
    metadata:              dict       = Field(default_factory=dict)
