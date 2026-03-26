import os
from dotenv import load_dotenv
from rota_service import RotaService
import json
from datetime import date, time
from decimal import Decimal
from uuid import UUID

from rota_connector.schemas.rota import (
    PracticeGridRequestSchema,
    PracticeContext,
    AvailableStaffRequestSchema,
    StaffContextEnriched,
    DaySlotContext,
    CreateAssignmentSchema,
    StaffContext,
    EditFollowingSchema,
    EditOccurrenceSchema,
    EditAllSchema,
    CancelOccurrenceSchema
)
from rota_connector.schemas.common import AssignmentType

# Load environment variables from .env
load_dotenv()

# 1. Initialize Service using environment variables
service = RotaService(
    client_id=os.getenv("ROTA_CLIENT_ID"), 
    client_secret=os.getenv("ROTA_CLIENT_SECRET"), 
    base_url=os.getenv("ROTA_BASE_URL", "http://localhost:8000")
)

# --- TEST FUNCTIONS ---

def run_availability_test(TARGET_DATE, PRACTICE_ID, ROLE_ID):
    payload = AvailableStaffRequestSchema(
        staff_contexts=[
            StaffContextEnriched(
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
            StaffContextEnriched(
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
        ]
    )
    print("Sending Availability request to ROTA Engine for date:", TARGET_DATE)
    try:
        response = service.get_available_staff(
            practice_id=PRACTICE_ID,
            target_date=TARGET_DATE,
            role_id=ROLE_ID,
            payload=payload
        )
        print("\n✅ Availability Results:")
        print(json.dumps(response, indent=2, default=str))
    except Exception as e:
        print("\n❌ Request failed!")
        print(f"Error: {str(e)}")

def run_practice_grid_test(WEEK_START, ROLE_ID, PRACTICE_1_ID, PRACTICE_2_ID, PRACTICE_HOURS_1, PRACTICE_HOURS_2):
    payload = PracticeGridRequestSchema(
        week_start=WEEK_START,
        role_id=ROLE_ID,
        practice_ids=[PRACTICE_1_ID, PRACTICE_2_ID],
        status_filter=None,
        practice_contexts={
            str(PRACTICE_1_ID): PracticeContext(required_hours=PRACTICE_HOURS_1),
            str(PRACTICE_2_ID): PracticeContext(required_hours=PRACTICE_HOURS_2)
        }
    )
    print(f"Loading Practice Grid for week starting {WEEK_START}...")
    try:
        response = service.get_practice_grid(payload=payload)
        print("\n✅ Practice Grid Extracted Successfully:")
        print(json.dumps(response, indent=2, default=str))
    except Exception as e:
        print("\n❌ Request failed!")
        print(f"Error: {str(e)}")

def run_staff_grid_test(service, WEEK_START, ROLE_ID, STAFF_ID, PRACTICE_ID):
    print(f"Fetching Staff Grid for week starting {WEEK_START}...")
    try:
        response = service.get_staff_grid(
            week_start=WEEK_START,
            role_id=ROLE_ID,
            staff_ids=str(STAFF_ID),
            practice_id=PRACTICE_ID
        )
        print("\n✅ Staff Grid Extracted Successfully:")
        print(json.dumps(response, indent=2, default=str))
    except Exception as e:
        print("\n❌ Request failed!")
        print(f"Error: {str(e)}")

def run_last_end_date_test(service, ROLE_ID, PRACTICE_ID):
    print(f"Fetching Last End Date for Practice: {PRACTICE_ID} | Role: {ROLE_ID}...")
    try:
        response = service.get_last_end_date(
            practice_id=PRACTICE_ID,
            role_id=ROLE_ID
        )
        print("\n✅ SLA Warning Data Fetched:")
        print(json.dumps(response, indent=2, default=str))
    except Exception as e:
        print("\n❌ Request failed!")
        print(f"Error: {str(e)}")

def run_create_assignment_test(service, STAFF_ID, PRACTICE_ID, ROLE_ID, TARGET_DATE, PRACTICE_HOURS):
    payload = CreateAssignmentSchema(
        staff_id=STAFF_ID,
        practice_id=PRACTICE_ID,
        role_id=ROLE_ID,
        assignment_type=AssignmentType.ONCE,
        date=TARGET_DATE,
        start_time=time(15, 0),
        end_time=time(16, 0),
        created_by_id=STAFF_ID,
        staff_context=StaffContext(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 1),
            weekly_capacity=Decimal("40.0"),
            day_slots=[
                DaySlotContext(day=0, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=1, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=2, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=3, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=4, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=5, start_time=time(9, 0), end_time=time(18, 0), is_active=True),
                DaySlotContext(day=6, start_time=time(0, 0), end_time=time(0, 0), is_active=False),
            ]
        ),
        practice_context=PracticeContext(required_hours=PRACTICE_HOURS)
    )
    print(f"Creating ONCE Assignment for Staff {STAFF_ID} on {TARGET_DATE}...")
    try:
        response = service.create_assignment(payload=payload)
        print("\n✅ Assignment Created Successfully!")
        print(json.dumps(response, indent=2, default=str))
    except Exception as e:
        print("\n❌ Request failed!")
        print(f"Error: {str(e)}")

def run_create_recurring_test(service, STAFF_ID, PRACTICE_ID, ROLE_ID, REC_START, REC_END, REC_RULE, PRACTICE_HOURS):
    payload = CreateAssignmentSchema(
        staff_id=STAFF_ID,
        practice_id=PRACTICE_ID,
        role_id=ROLE_ID,
        assignment_type=AssignmentType.RECURRING,
        start_time=time(10, 0),
        end_time=time(15, 0),
        created_by_id=STAFF_ID, 
        recurrence_start=REC_START,
        recurrence_end=REC_END,
        recurrence_rule=REC_RULE,
        staff_context=StaffContext(
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 1),
            weekly_capacity=Decimal("40.0"),
            day_slots=[
                DaySlotContext(day=0, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=1, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=2, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=3, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=4, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=5, start_time=time(9, 0), end_time=time(13, 0), is_active=True),
                DaySlotContext(day=6, start_time=time(0, 0), end_time=time(0, 0), is_active=False),
            ]
        ),
        practice_context=PracticeContext(required_hours=PRACTICE_HOURS)
    )
    print(f"Creating RECURRING Assignment starting {REC_START}...")
    try:
        response = service.create_assignment(payload=payload)
        print("\n✅ Recurring Assignment Created Successfully!")
        print(json.dumps(response, indent=2, default=str))
    except Exception as e:
        print("\n❌ Request failed!")
        print(f"Error: {str(e)}")

def run_edit_occurrence_test(service, ASSIGNMENT_ID, ORIGINAL_DATE, PRACTICE_HOURS):
    payload = EditOccurrenceSchema(
        original_date=ORIGINAL_DATE,
        start_time=time(10, 0),
        end_time=time(15, 0),
        staff_context=StaffContext(
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 1),
            weekly_capacity=Decimal("40.0"),
            day_slots=[
                DaySlotContext(day=0, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=1, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=2, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=3, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=4, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=5, start_time=time(9, 0), end_time=time(13, 0), is_active=True),
                DaySlotContext(day=6, start_time=time(0, 0), end_time=time(0, 0), is_active=False),
            ]
        ),
        practice_context=PracticeContext(required_hours=PRACTICE_HOURS)
    )
    print(f"Editing OCCURRENCE on {ORIGINAL_DATE}...")
    try:
        response = service.edit_occurrence(assignment_id=ASSIGNMENT_ID, payload=payload)
        print("\n✅ Occurrence Exception Created Successfully!")
        print(json.dumps(response, indent=2, default=str))
    except Exception as e:
        print("\n❌ Request failed!")
        print(f"Error: {str(e)}")

def run_edit_following_test(service, ASSIGNMENT_ID, FROM_DATE, PRACTICE_HOURS):
    payload = EditFollowingSchema(
        from_date=FROM_DATE,
        start_time=time(10, 0),
        end_time=time(14, 0),
        staff_context=StaffContext(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 1),
            weekly_capacity=Decimal("40.0"),
            day_slots=[
                DaySlotContext(day=0, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=1, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=2, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=3, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=4, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=5, start_time=time(9, 0), end_time=time(13, 0), is_active=True),
                DaySlotContext(day=6, start_time=time(0, 0), end_time=time(0, 0), is_active=False),
            ]
        ),
        practice_context=PracticeContext(required_hours=PRACTICE_HOURS)
    )
    print(f"Applying EDIT FOLLOWING starting {FROM_DATE}...")
    try:
        response = service.edit_following(assignment_id=ASSIGNMENT_ID, payload=payload)
        print("\n✅ Assignment Successfully Split and Updated!")
        print(json.dumps(response, indent=2, default=str))
    except Exception as e:
        print("\n❌ Request failed!")
        print(f"Error: {str(e)}")

def run_edit_all_test(service, ASSIGNMENT_ID, PRACTICE_HOURS):
    payload = EditAllSchema(
        start_time=time(9, 0),
        end_time=time(12, 0),
        staff_context=StaffContext(
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
            weekly_capacity=Decimal("40.0"),
            day_slots=[
                DaySlotContext(day=0, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=1, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=2, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=3, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=4, start_time=time(9, 0), end_time=time(17, 0), is_active=True),
                DaySlotContext(day=5, start_time=time(0, 0), end_time=time(0, 0), is_active=False),
                DaySlotContext(day=6, start_time=time(0, 0), end_time=time(0, 0), is_active=False),
            ]
        ),
        practice_context=PracticeContext(required_hours=PRACTICE_HOURS)
    )
    print(f"Applying EDIT ALL to Assignment {ASSIGNMENT_ID}...")
    try:
        response = service.edit_all(assignment_id=ASSIGNMENT_ID, payload=payload)
        print("\n✅ Master Assignment Successfully Updated!")
        print(json.dumps(response, indent=2, default=str))
    except Exception as e:
        print("\n❌ Request failed!")
        print(f"Error: {str(e)}")

def run_cancel_occurrence_test(service, ASSIGNMENT_ID, CANCEL_DATE):
    payload = CancelOccurrenceSchema(date=CANCEL_DATE)
    print(f"Canceling occurrence on {CANCEL_DATE}...")
    try:
        response = service.cancel_occurrence(assignment_id=ASSIGNMENT_ID, payload=payload)
        print("\n✅ Occurrence Cancelled Successfully!")
        print(json.dumps(response, indent=2, default=str))
    except Exception as e:
        print("\n❌ Request failed!")
        print(f"Error: {str(e)}")

def run_delete_assignment_test(service, ASSIGNMENT_ID):
    print(f"Hard Deleting Assignment {ASSIGNMENT_ID}...")
    try:
        response = service.delete_assignment(assignment_id=ASSIGNMENT_ID)
        print("\n✅ Assignment Hard Deleted Successfully!")
        print("Response:", response)
    except Exception as e:
        print("\n❌ Request failed!")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Check Service Health
    print("Checking ROTA Service Health...")
    health_status = service.check_health()
    print("Health Status:", health_status) 

    # --- TEST CONSTANTS ---
    ROLE_ID = UUID("c3d4e5f6-a7b8-9012-cdef-123456789012")
    PRACTICE_ID = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    STAFF_ID = UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901")
    TARGET_DATE = date(2026, 7, 23)
    WEEK_START = date(2026, 7, 20)
    PRACTICE_1_ID = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    PRACTICE_2_ID = UUID("a1b2c3d4-0000-0000-0000-000000000002")
    PRACTICE_HOURS_1 = Decimal("20.0")
    PRACTICE_HOURS_2 = Decimal("40.0")
    ASSIGNMENT_ID = UUID("43db8b52-45ce-47a6-b090-573c1e28aa70")
    CANCEL_DATE = date(2027, 7, 23)
    FROM_DATE = date(2026, 7, 21)
    PRACTICE_HOURS = Decimal("40.0")
    REC_START = date(2027, 7, 23)
    REC_END = date(2027, 7, 30)
    REC_RULE = "FREQ=WEEKLY;BYDAY=MO,WE,FR;INTERVAL=1"
    ORIGINAL_DATE = date(2027, 7, 26)

    # --- RUN SELECTED TEST ---
    run_availability_test(TARGET_DATE, PRACTICE_ID, ROLE_ID)
    run_practice_grid_test(WEEK_START, ROLE_ID, PRACTICE_1_ID, PRACTICE_2_ID, PRACTICE_HOURS_1, PRACTICE_HOURS_2)
    run_staff_grid_test(service, WEEK_START, ROLE_ID, STAFF_ID, PRACTICE_ID)
    run_last_end_date_test(service, ROLE_ID, PRACTICE_ID)
    run_create_assignment_test(service, STAFF_ID, PRACTICE_ID, ROLE_ID, TARGET_DATE, PRACTICE_HOURS)
    run_create_recurring_test(service, STAFF_ID, PRACTICE_ID, ROLE_ID, REC_START, REC_END, REC_RULE, PRACTICE_HOURS)
    run_edit_occurrence_test(service, ASSIGNMENT_ID, ORIGINAL_DATE, PRACTICE_HOURS)
    run_edit_following_test(service, ASSIGNMENT_ID, FROM_DATE, PRACTICE_HOURS)
    run_edit_all_test(service, ASSIGNMENT_ID, PRACTICE_HOURS)
    run_cancel_occurrence_test(service, ASSIGNMENT_ID, CANCEL_DATE)
    run_delete_assignment_test(service, ASSIGNMENT_ID)
