import uuid
from datetime import date, time, datetime
from decimal import Decimal

from rota_connector.schemas.rota import (
    CreateAssignmentSchema,
    PracticeGridRequestSchema,
    StaffContext,
    PracticeContext,
    AssignmentType,
    AvailableStaffRequestSchema,
    EditOccurrenceSchema,
    CancelOccurrenceSchema
)

def test_practice_grid(connector, httpx_mock):
    payload = PracticeGridRequestSchema(
        week_start=date(2026, 4, 1),
        role_id=uuid.uuid4(),
        status_filter="unallocated",
        practice_contexts={}
    )

    httpx_mock.add_response(
        method="POST",
        url=f"{connector._base_client.base_url}/api/v1/rota/grid/practice",
        json={"data": [{"practice_id": str(uuid.uuid4())}]}
    )

    result = connector.rota.practice_grid(payload)
    assert len(result) == 1
    assert "practice_id" in result[0]

def test_staff_grid(connector, httpx_mock):
    role_id = uuid.uuid4()
    week_start = date(2026, 4, 1)
    
    httpx_mock.add_response(
        method="GET",
        url=f"{connector._base_client.base_url}/api/v1/rota/grid/staff?week_start=2026-04-01&role_id={role_id}",
        json={"data": [{"staff_id": str(uuid.uuid4())}]}
    )

    result = connector.rota.staff_grid(week_start, role_id)
    assert len(result) == 1

def test_create_assignment(connector, httpx_mock):
    payload = CreateAssignmentSchema(
        staff_id=uuid.uuid4(),
        practice_id=uuid.uuid4(),
        role_id=uuid.uuid4(),
        assignment_type=AssignmentType.ONCE,
        start_time=time(9, 0),
        end_time=time(17, 0),
        date=date(2026, 4, 5),
        staff_context=StaffContext(
            start_date=date(2024, 1, 1),
            weekly_capacity=Decimal("40"),
            day_slots=[]
        ),
        practice_context=PracticeContext(required_hours=Decimal("40"))
    )

    httpx_mock.add_response(
        method="POST",
        url=f"{connector._base_client.base_url}/api/v1/rota/assignments",
        json={"data": {"id": str(uuid.uuid4()), "staff_id": str(payload.staff_id)}}
    )

    result = connector.rota.create_assignment(payload)
    assert result["staff_id"] == str(payload.staff_id)

def test_cancel_occurrence(connector, httpx_mock):
    assignment_id = uuid.uuid4()
    payload = CancelOccurrenceSchema(date=date(2026, 4, 5))

    httpx_mock.add_response(
        method="POST",
        url=f"{connector._base_client.base_url}/api/v1/rota/assignments/{assignment_id}/cancel-occurrence",
        json={"data": {"assignment_id": str(assignment_id), "is_exception": True}}
    )

    result = connector.rota.cancel_occurrence(assignment_id, payload)
    assert result["is_exception"] is True


def test_get_assignment(connector, httpx_mock):
    """get_assignment fetches a single active assignment by ID."""
    assignment_id = uuid.uuid4()
    staff_id = uuid.uuid4()

    httpx_mock.add_response(
        method="GET",
        url=f"{connector._base_client.base_url}/api/v1/rota/assignments/{assignment_id}",
        json={
            "data": {
                "id": str(assignment_id),
                "staff_id": str(staff_id),
                "deleted_at": None,
                "deleted_by_id": None,
            }
        },
    )

    result = connector.rota.get_assignment(assignment_id)
    assert result["id"] == str(assignment_id)
    assert result["deleted_at"] is None


def test_delete_assignment_with_deleted_by_id(connector, httpx_mock):
    """delete_assignment passes deleted_by_id as a query param and returns full assignment data."""
    assignment_id = uuid.uuid4()
    deleted_by_id = uuid.uuid4()
    staff_id = uuid.uuid4()

    httpx_mock.add_response(
        method="DELETE",
        url=(
            f"{connector._base_client.base_url}/api/v1/rota/assignments/{assignment_id}"
            f"?deleted_by_id={deleted_by_id}"
        ),
        json={
            "data": {
                "id": str(assignment_id),
                "staff_id": str(staff_id),
                "hours": "4.00",
                "deleted_at": "2026-04-02T12:00:00Z",
                "deleted_by_id": str(deleted_by_id),
            },
            "message": "Assignment deleted successfully",
        },
    )

    result = connector.rota.delete_assignment(assignment_id, deleted_by_id=deleted_by_id)
    assert result["id"] == str(assignment_id)
    assert result["deleted_by_id"] == str(deleted_by_id)
    assert result["deleted_at"] is not None


def test_delete_assignment_without_deleted_by_id(connector, httpx_mock):
    """delete_assignment works without deleted_by_id — no query param sent."""
    assignment_id = uuid.uuid4()

    httpx_mock.add_response(
        method="DELETE",
        url=f"{connector._base_client.base_url}/api/v1/rota/assignments/{assignment_id}",
        json={
            "data": {
                "id": str(assignment_id),
                "deleted_at": "2026-04-02T12:00:00Z",
                "deleted_by_id": None,
            },
            "message": "Assignment deleted successfully",
        },
    )

    result = connector.rota.delete_assignment(assignment_id)
    assert result["id"] == str(assignment_id)
    assert result["deleted_by_id"] is None
