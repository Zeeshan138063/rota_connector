"""
ROTA Service Integration Template

This module provides a pre-built integration layer for the ROTA Connector SDK.
You can copy and drop this file directly into your own backend application 
(Django, FastAPI, Flask, etc.) and inject your specific credentials to instantly 
access all ROTA Assignment and Scheduling engine capabilities.

Usage:
------
    # 1. Initialize your service once when the app starts
    from my_app.services.rota_service import RotaService
    
    rota_service = RotaService(
        client_id="YOUR_PROJECT_CLIENT_ID",
        client_secret="YOUR_PROJECT_CLIENT_SECRET",
        base_url="https://rota-backend.31g.co.uk" # Or your private instance URL
    )

    # 2. Call any available SDK method!
    available_staff = rota_service.get_available_staff(
        practice_id=..., target_date=..., role_id=..., payload=...
    )
"""

from datetime import date
from typing import Any, Optional
from uuid import UUID

from rota_connector import RotaConnector
from rota_connector.schemas.project import ProjectCreateSchema
from rota_connector.schemas.rota import (
    AvailableStaffRequestSchema,
    CancelOccurrenceSchema,
    CreateAssignmentSchema,
    EditAllSchema,
    EditFollowingSchema,
    EditOccurrenceSchema,
    PracticeGridRequestSchema,
)


class RotaService:
    """Wrapper service class around the RotaConnector SDK."""
    
    def __init__(self, client_id: str, client_secret: str, base_url: Optional[str] = None):
        """
        Initialize the connector and set global project credentials.
        These credentials will be automatically injected into every request header.
        
        Args:
            client_id (str): The unique Project Client ID from ROTA Core.
            client_secret (str): The Project Client Secret.
            base_url (str, optional): Overrides the default ROTA API url (e.g. for localhost testing).
        """
        kwargs = {}
        if base_url:
            kwargs["base_url"] = base_url
            
        self.connector = RotaConnector(**kwargs)
        self.connector.set_credentials(client_id, client_secret)

    def check_health(self) -> Any:
        """
        Check the connectivity and status of the ROTA Core Service.
        
        Returns:
            JSON object `{ "status": "ok", "service": "rota-backend" }`
        """
        return self.connector.health()

    # ── Grid & Availability ───────────────────────────────────────────────────

    def get_practice_grid(self, payload: PracticeGridRequestSchema) -> Any:
        """
        Fetch the practice schedule grid to view open requirements and allocations.
        
        The ROTA Engine operates neutrally via contexts. This allows you to evaluate your
        internal Staff/Practice setup dynamically without the engine permanently storing it.

        Args:
            payload (PracticeGridRequestSchema):
                - week_start (date): The starting date for the 7-day grid view.
                - role_id (UUID): Filter applicable role ID (e.g. 'nurse', 'doctor').
                - practice_ids (List[UUID]): Filter grid to specific practices.
                - status_filter (str): 'unallocated', 'partially_allocated', or 'fully_allocated'.
                - practice_contexts (dict): Supply the required hours logic dynamically for each
                  queried practice, e.g., `{"practice_uuid": PracticeContext(required_hours=40)}`.
                  
        Returns:
            List of `PracticeGridOut` objects detailing allocated vs required hours per day.
        """
        return self.connector.rota.practice_grid(payload)

    def get_staff_grid(
        self, 
        week_start: date, 
        role_id: UUID, 
        staff_ids: Optional[str] = None, 
        practice_id: Optional[UUID] = None
    ) -> Any:
        """
        Fetch the staff schedule grid to view individual working shifts.
        
        This will return the precise occurrence-level allocations for each staff member, 
        including any specific start/end times per day in the target week.

        Args:
            week_start (date): The starting date for the 7-day view.
            role_id (UUID): The role being queried.
            staff_ids (str, optional): A comma-separated list of UUID strings to filter down.
            practice_id (UUID, optional): Filter occurrences specifically mapping to a practice.
            
        Returns:
            List of `StaffGridOut` containing daily occurrence timelines.
        """
        return self.connector.rota.staff_grid(
            week_start=week_start, 
            role_id=role_id, 
            staff_ids=staff_ids, 
            practice_id=practice_id
        )

    def get_available_staff(
        self, 
        practice_id: UUID, 
        target_date: date, 
        role_id: UUID, 
        payload: AvailableStaffRequestSchema
    ) -> Any:
        """
        Query the ROTA engine for real-time staff availability over a target date.
        
        The ROTA backend acts as a calculation engine. You pass in all potential staff and 
        their individual working rules/hours, and the engine cross-references them against 
        existing allocations, returning exactly who can take the shift and how much capacity 
        they have left.

        Args:
            practice_id (UUID): The practice requesting staff.
            target_date (date): The exact date you want to evaluate availability.
            role_id (UUID): Role requirement.
            payload (AvailableStaffRequestSchema):
                Requires `staff_contexts` = List of `StaffContextEnriched`.
                Each staff context must define:
                - staff_id (UUID)
                - start_date / end_date (contract boundaries)
                - weekly_capacity (Decimal of maximum hours they can theoretically work)
                - day_slots (List of generic Shift availabilities: day(0=Mon-6=Sun), start, end, is_active).

        Returns:
            AvailabilityResponseSchemaBase: A mix of `available_staff` (those who can take the shift,
            along with capacity stats) and `currently_assigned` (who is already physically booked).
        """
        return self.connector.rota.available_staff(
            practice_id=practice_id, 
            target_date=target_date, 
            role_id=role_id, 
            payload=payload
        )

    # ── Assignments Management ────────────────────────────────────────────────

    def get_last_end_date(self, practice_id: UUID, role_id: UUID) -> Any:
        """
        Fetch the furthest scheduled assignment date for a practice and role.
        Useful when you want to bulk-produce new recurring grids starting exactly where
        the previous one left off!

        Args:
            practice_id (UUID): The practice.
            role_id (UUID): The role.
            
        Returns:
            JSON object `{ "last_end_date": "2026-10-15" }` or None.
        """
        return self.connector.rota.last_end_date(practice_id=practice_id, role_id=role_id)

    def create_assignment(self, payload: CreateAssignmentSchema) -> Any:
        """
        Create a new ONE-OFF or RECURRING assignment. 
        Engine natively resolves recurring shifts into expanded daily Occurrences.

        Args:
            payload (CreateAssignmentSchema):
                - staff_id, practice_id, role_id
                - assignment_type: `AssignmentType.ONCE` or `AssignmentType.RECURRING`
                - start_time, end_time (time structure for the shift)
                - staff_context: Pass the staff's capacity and slot rules dynamically.
                - practice_context: Pass the practice's active hour requirements dynamically.
                FOR ONCE:
                    - date: explicitly provide the single date.
                FOR RECURRING:
                    - recurrence_start, recurrence_end (date boundaries of the loop)
                    - recurrence_rule (RRULE format, e.g. "FREQ=WEEKLY;BYDAY=MO,WE,FR")
                    
        Returns:
            The generated `AssignmentOut` object representing the master configuration.
        """
        return self.connector.rota.create_assignment(payload)

    def edit_occurrence(self, assignment_id: UUID, payload: EditOccurrenceSchema) -> Any:
        """
        Edit only a SINGLE occurrence of a recurring series (creates an exception flag).
        The master recurrence rule remains unchanged, but a specific node takes a new shape.

        Args:
            assignment_id (UUID): ID of the parent assignment to modify.
            payload (EditOccurrenceSchema):
                - original_date: The exact date this occurrence was initially supposed to happen.
                - start_time / end_time: The new substituted hours for this specific day.
                - staff_context / practice_context: Live quota contexts.
        """
        return self.connector.rota.edit_occurrence(assignment_id, payload)

    def edit_following(self, assignment_id: UUID, payload: EditFollowingSchema) -> Any:
        """
        Edit a single occurrence AND all subsequent occurrences, effectively splitting the series.
        This modifies the end-date of the current series and generates an entirely new clone
        series that kicks off from 'from_date' forwards with the new settings.

        Args:
            assignment_id (UUID): The parent assignment to split.
            payload (EditFollowingSchema):
                - from_date: The date from which the new rule overrides begin.
                - start_time / end_time: The new standard times.
                - staff_context, practice_context.
        """
        return self.connector.rota.edit_following(assignment_id, payload)

    def edit_all(self, assignment_id: UUID, payload: EditAllSchema) -> Any:
        """
        Edit the core definition of the recurring master series. 
        This change cascades backward and forward across all non-exception nodes.

        Args:
            assignment_id (UUID): The assignment core to mutate.
            payload (EditAllSchema):
                - start_time / end_time: Baseline adjustments for the entire duration.
                - staff_context, practice_context.
                - Optional RRULE adjustments (`date`, `recurrence_start/end`, `recurrence_rule`).
        """
        return self.connector.rota.edit_all(assignment_id, payload)

    def cancel_occurrence(self, assignment_id: UUID, payload: CancelOccurrenceSchema) -> Any:
        """
        Cancel a single specific occurrence within a recurring series.
        Creates an Exception mapping the day to logical deletion.

        Args:
            assignment_id (UUID): The parent assignment.
            payload (CancelOccurrenceSchema):
                - date (date): The exact date within the series to prune.
        """
        return self.connector.rota.cancel_occurrence(assignment_id, payload)

    def delete_assignment(self, assignment_id: UUID) -> Any:
        """
        Hard delete an entire assignment and all associated occurrences.

        Args:
            assignment_id (UUID): Targets the core `AssignmentOut` ID.
        """
        return self.connector.rota.delete_assignment(assignment_id)

    # ── Projects Management (Admin Only) ──────────────────────────────────────

    def register_project(self, payload: ProjectCreateSchema) -> Any:
        """
        Register a new Client Project to gain a new pair of Client Credentials.
        Note: This is an admin/global command that usually does not require authentication.
        
        Args:
            payload (ProjectCreateSchema):
                - name (str): Display name for the consumed project.
                - description (str, optional).
                
        Returns:
            JSON object containing `client_id` and the raw `client_secret`.
        """
        return self.connector.projects.register_project(payload)

    def rotate_secret(self, project_id: UUID) -> Any:
        """
        Rotate and retrieve a new client_secret for an existing platform project.
        The old secret will immediately lose validity.

        Args:
            project_id (UUID): The UUID (usually mapping to `client_id`) of the project.
            
        Returns:
            JSON object containing the newly generated `client_secret`.
        """
        return self.connector.projects.rotate_secret(project_id)
