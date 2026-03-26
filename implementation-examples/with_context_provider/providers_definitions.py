from uuid import UUID
from datetime import date, time
from decimal import Decimal
from typing import List, Optional

from rota_connector.interfaces.resource_provider import IResourceProvider
from rota_connector.interfaces.context_provider import IContextProvider
from rota_connector.schemas.rota import StaffContextEnriched, PracticeContext, DaySlotContext
from rota_connector.schemas.common import DateRangeFilter
from rota_connector.exceptions import EntityNotFoundError, ContextNotFoundError

class StaffProvider(IResourceProvider):
    """
    Mock implementation of IResourceProvider using hardcoded data.
    In a real app, this would query your Users/Staff database.
    """
    
    def __init__(self):
        # Mock database
        self.staff_db = {
            UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901"): StaffContextEnriched(
                staff_id=UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901"),
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 1),
                weekly_capacity=Decimal("40.0"),
                day_slots=[
                    DaySlotContext(day=0, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                    DaySlotContext(day=1, start_time=time(9, 0), end_time=time(16, 0), is_active=True),
                    DaySlotContext(day=2, start_time=time(9, 0), end_time=time(15, 0), is_active=True),
                    DaySlotContext(day=3, start_time=time(9, 0), end_time=time(14, 0), is_active=True),
                    DaySlotContext(day=4, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                    DaySlotContext(day=5, start_time=time(9, 0), end_time=time(13, 0), is_active=True),
                    DaySlotContext(day=6, start_time=time(0, 0), end_time=time(0, 0), is_active=False),
                ]
            ),
            UUID("e1f2b3c4-d5e6-aea1-b7c1-f12345678901"): StaffContextEnriched(
                staff_id=UUID("e1f2b3c4-d5e6-aea1-b7c1-f12345678901"),
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 1),
                weekly_capacity=Decimal("20.0"),
                day_slots=[
                    DaySlotContext(day=0, start_time=time(8, 0), end_time=time(12, 0), is_active=True),
                    DaySlotContext(day=1, start_time=time(8, 0), end_time=time(12, 0), is_active=True),
                    DaySlotContext(day=2, start_time=time(9, 0), end_time=time(16, 0), is_active=True),
                    DaySlotContext(day=3, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                ]
            )
        }

    def get_staff_context(self, staff_id: UUID, date_range: Optional[DateRangeFilter] = None) -> StaffContextEnriched:
        if staff_id not in self.staff_db:
            raise EntityNotFoundError(f"Staff {staff_id} not found in mock DB")
        return self.staff_db[staff_id]

    def list_staff_contexts(self, practice_id: Optional[UUID] = None, is_active: bool = True, skip: int = 0, limit: int = 100) -> List[StaffContextEnriched]:
        # Return all mock staff (ignoring filters for simplicity)
        return list(self.staff_db.values())


class PracticeProvider(IContextProvider):
    """
    Mock implementation of IContextProvider using hardcoded data.
    In a real app, this would query your Practice/Location database.
    """

    def __init__(self):
        # Mock database
        self.practice_db = {
            UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"): PracticeContext(required_hours=Decimal("40.0")),
            UUID("a1b2c3d4-0000-0000-0000-000000000002"): PracticeContext(required_hours=Decimal("20.0"))
        }

    def get_practice_context(self, practice_id: UUID) -> PracticeContext:
        if practice_id not in self.practice_db:
            raise ContextNotFoundError(f"Practice {practice_id} not found in mock DB")
        return self.practice_db[practice_id]

    def list_practice_contexts(self, is_active: bool = True, skip: int = 0, limit: int = 100) -> List[PracticeContext]:
        return list(self.practice_db.values())

    def validate_entity_in_context(self, staff_id: UUID, practice_id: UUID) -> bool:
        # Mock validation: assume all staff are allowed at all practices for this demo
        return True
