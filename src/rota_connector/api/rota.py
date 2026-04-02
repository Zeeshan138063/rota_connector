from datetime import date
from typing import Any, Optional
from uuid import UUID

from rota_connector.base_client import BaseClient
from rota_connector.schemas.rota import (
    AvailableStaffRequestSchema,
    CancelOccurrenceSchema,
    CreateAssignmentSchema,
    EditAllSchema,
    EditFollowingSchema,
    EditOccurrenceSchema,
    PracticeGridRequestSchema,
)


class RotaAPI:
    """Client for rota assignment endpoints."""

    def __init__(self, client: BaseClient, version: str = "v1"):
        self.client = client
        self.version = version

    def _base(self) -> str:
        return "/api/v1/rota"

    def practice_grid(self, payload: PracticeGridRequestSchema) -> Any:
        """Get Practice Grid."""
        response = self.client.post(f"{self._base()}/grid/practice", json=payload.model_dump(mode="json"))
        return response.get("data") if response and "data" in response else response

    def staff_grid(
        self,
        week_start: date,
        role_id: UUID,
        staff_ids: Optional[str] = None,
        practice_id: Optional[UUID] = None,
    ) -> Any:
        """Get Staff Grid."""
        params: dict[str, Any] = {
            "week_start": week_start.isoformat(),
            "role_id": str(role_id),
        }
        if staff_ids:
            params["staff_ids"] = staff_ids
        if practice_id:
            params["practice_id"] = str(practice_id)
        
        response = self.client.get(f"{self._base()}/grid/staff", params=params)
        return response.get("data") if response and "data" in response else response

    def last_end_date(self, practice_id: UUID, role_id: UUID) -> Any:
        """Get Last End Date."""
        params = {"practice_id": str(practice_id), "role_id": str(role_id)}
        response = self.client.get(f"{self._base()}/assignments/last-end-date", params=params)
        return response.get("data") if response and "data" in response else response

    def available_staff(
        self,
        practice_id: UUID,
        target_date: date,
        role_id: UUID,
        payload: AvailableStaffRequestSchema,
    ) -> Any:
        """Get Available Staff."""
        params = {
            "practice_id": str(practice_id),
            "date": target_date.isoformat(),
            "role_id": str(role_id),
        }
        response = self.client.post(f"{self._base()}/available-staff", params=params, json=payload.model_dump(mode="json"))
        return response.get("data") if response and "data" in response else response

    def create_assignment(self, payload: CreateAssignmentSchema) -> Any:
        """Create Assignment."""
        response = self.client.post(f"{self._base()}/assignments", json=payload.model_dump(mode="json", exclude_unset=True))
        return response.get("data") if response and "data" in response else response

    def edit_occurrence(self, assignment_id: UUID, payload: EditOccurrenceSchema) -> Any:
        """Edit a single occurrence of a recurring assignment."""
        response = self.client.patch(
            f"{self._base()}/assignments/{assignment_id}/edit-occurrence",
            json=payload.model_dump(mode="json")
        )
        return response.get("data") if response and "data" in response else response

    def edit_following(self, assignment_id: UUID, payload: EditFollowingSchema) -> Any:
        """Edit this occurrence and all following ones by splitting the assignment."""
        response = self.client.patch(
            f"{self._base()}/assignments/{assignment_id}/edit-following",
            json=payload.model_dump(mode="json")
        )
        return response.get("data") if response and "data" in response else response

    def edit_all(self, assignment_id: UUID, payload: EditAllSchema) -> Any:
        """Update all occurrences by modifying the master record."""
        response = self.client.patch(
            f"{self._base()}/assignments/{assignment_id}/edit-all",
            json=payload.model_dump(mode="json", exclude_unset=True)
        )
        return response.get("data") if response and "data" in response else response

    def cancel_occurrence(self, assignment_id: UUID, payload: CancelOccurrenceSchema) -> Any:
        """Cancel a single occurrence."""
        response = self.client.post(
            f"{self._base()}/assignments/{assignment_id}/cancel-occurrence",
            json=payload.model_dump(mode="json")
        )
        return response.get("data") if response and "data" in response else response

    def get_assignment(self, assignment_id: UUID) -> Any:
        """Retrieve a single active assignment by ID."""
        response = self.client.get(f"{self._base()}/assignments/{assignment_id}")
        return response.get("data") if response and "data" in response else response

    def delete_assignment(
        self,
        assignment_id: UUID,
        deleted_by_id: Optional[UUID] = None,
    ) -> Any:
        """Soft-delete an assignment.

        Returns the full assignment data (hours, recurrence dates, etc.) so the
        caller can reverse allocation deltas without maintaining a local mirror.

        Args:
            assignment_id: The assignment to delete.
            deleted_by_id: Optional ID of the user performing the deletion.
        """
        params: dict[str, Any] = {}
        if deleted_by_id:
            params["deleted_by_id"] = str(deleted_by_id)

        response = self.client.delete(
            f"{self._base()}/assignments/{assignment_id}",
            params=params if params else None,
        )
        return response.get("data") if response and "data" in response else response
