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
