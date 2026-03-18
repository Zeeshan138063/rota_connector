import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator, Field, computed_field

from rota_connector.schemas.common import AssignmentType


# Context schemas
class DaySlotContext(BaseModel):
    day: int = Field(..., description="0=Mon ... 6=Sun")
    start_time: datetime.time
    end_time: datetime.time
    is_active: bool


class StaffContext(BaseModel):
    start_date: datetime.date = Field(..., description="Contract start date")
    end_date: Optional[datetime.date] = Field(None, description="Contract end date")
    weekly_capacity: Decimal
    day_slots: list[DaySlotContext]


class StaffContextEnriched(StaffContext):
    staff_id: UUID


class PracticeContext(BaseModel):
    required_hours: Decimal


def _compute_hours(start_time: datetime.time, end_time: datetime.time) -> Decimal:
    start_dt = datetime.datetime.combine(datetime.date.today(), start_time)
    end_dt = datetime.datetime.combine(datetime.date.today(), end_time)
    delta = end_dt - start_dt
    return Decimal(str(round(delta.total_seconds() / 3600, 2)))


class CreateAssignmentSchema(BaseModel):
    staff_id: UUID
    practice_id: UUID
    role_id: UUID
    assignment_type: AssignmentType
    start_time: datetime.time
    end_time: datetime.time
    created_by_id: Optional[UUID] = None
    staff_context: StaffContext
    practice_context: PracticeContext

    date: Optional[datetime.date] = None
    recurrence_start: Optional[datetime.date] = None
    recurrence_end: Optional[datetime.date] = None
    recurrence_rule: Optional[str] = None

    @computed_field
    @property
    def hours(self) -> Decimal:
        return _compute_hours(self.start_time, self.end_time)

    @model_validator(mode="after")
    def validate_by_type(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")
        if self.assignment_type == AssignmentType.ONCE:
            if not self.date:
                raise ValueError("date is required for ONCE assignment.")
        if self.assignment_type == AssignmentType.RECURRING:
            if not all(
                [self.recurrence_start, self.recurrence_end, self.recurrence_rule]
            ):
                raise ValueError(
                    "recurrence_start, recurrence_end, recurrence_rule "
                    "are required for RECURRING assignment."
                )
        return self


class PracticeGridRequestSchema(BaseModel):
    week_start: datetime.date
    role_id: UUID
    practice_ids: Optional[list[UUID]] = None
    status_filter: Optional[str] = Field(
        None,
        description="null | 'unallocated' | 'partially_allocated' | 'fully_allocated'",
    )
    practice_contexts: dict[str, PracticeContext]


class AvailableStaffRequestSchema(BaseModel):
    staff_contexts: list[StaffContextEnriched]


class EditOccurrenceSchema(BaseModel):
    original_date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    staff_context: StaffContext
    practice_context: PracticeContext

    @computed_field
    @property
    def hours(self) -> Decimal:
        return _compute_hours(self.start_time, self.end_time)

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")
        return self


class EditFollowingSchema(BaseModel):
    from_date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    staff_context: StaffContext
    practice_context: PracticeContext

    @computed_field
    @property
    def hours(self) -> Decimal:
        return _compute_hours(self.start_time, self.end_time)

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")
        return self


class EditAllSchema(BaseModel):
    start_time: datetime.time
    end_time: datetime.time
    staff_context: StaffContext
    practice_context: PracticeContext

    assignment_type: Optional[AssignmentType] = None
    date: Optional[datetime.date] = None
    recurrence_start: Optional[datetime.date] = None
    recurrence_end: Optional[datetime.date] = None
    recurrence_rule: Optional[str] = None

    @computed_field
    @property
    def hours(self) -> Decimal:
        return _compute_hours(self.start_time, self.end_time)

    @model_validator(mode="after")
    def validate_all(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")

        if self.assignment_type == AssignmentType.ONCE:
            if not self.date:
                raise ValueError("date is required when changing to ONCE.")
        elif self.assignment_type == AssignmentType.RECURRING:
            if not all([self.recurrence_start, self.recurrence_end, self.recurrence_rule]):
                raise ValueError(
                    "recurrence_start, recurrence_end, recurrence_rule "
                    "are required when changing to RECURRING."
                )
        return self


class CancelOccurrenceSchema(BaseModel):
    date: datetime.date


# Response schemas
class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    staff_id: UUID
    practice_id: UUID
    role_id: UUID
    assignment_type: AssignmentType
    start_time: datetime.time
    end_time: datetime.time
    hours: Decimal
    date: Optional[datetime.date] = None
    recurrence_start: Optional[datetime.date] = None
    recurrence_end: Optional[datetime.date] = None
    recurrence_rule: Optional[str] = None
    created_at: datetime.datetime


class OccurrenceOut(BaseModel):
    date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    hours: Decimal
    assignment_id: UUID
    practice_id: UUID
    staff_id: UUID
    is_exception: bool


class StaffGridDay(BaseModel):
    date: datetime.date
    occurrences: list[OccurrenceOut]


class StaffGridOut(BaseModel):
    staff_id: UUID
    days: list[StaffGridDay]


class PracticeGridDay(BaseModel):
    date: datetime.date
    allocated: Decimal
    remaining: Decimal
    status: str
    assignments: list[OccurrenceOut]


class PracticeGridOut(BaseModel):
    practice_id: UUID
    required_hours: Decimal
    allocated_hours: Decimal
    left_hours: Decimal
    days: list[PracticeGridDay]


class AvailableStaffOut(BaseModel):
    staff_id: UUID
    role_id: UUID
    day_start: Optional[datetime.time] = None
    day_end: Optional[datetime.time] = None
    weekly_capacity: Decimal
    weekly_assigned: Decimal
    remaining_capacity: Decimal


class AvailabilityResponseSchemaBase(BaseModel):
    available_staff: list[AvailableStaffOut]
    currently_assigned: list[OccurrenceOut]
