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
        base_url="https://rota-backend.31g.co.uk", # Or your private instance URL
        staff_provider=MyDjangoStaffProvider(),
        practice_provider=MyDjangoPracticeProvider()
    )

    # 2. Call any available SDK method!
    # With providers, payloads auto-hydrate!
    available_staff = rota_service.auto_get_available_staff(
        practice_id=..., target_date=..., role_id=...
    )
"""

from datetime import date
from typing import Any, Optional
from uuid import UUID

from rota_connector import RotaConnector
from rota_connector.interfaces.context_provider import IContextProvider
from rota_connector.interfaces.resource_provider import IResourceProvider
from rota_connector.schemas.common import DateRangeFilter
from rota_connector.schemas.project import ProjectCreateSchema
from rota_connector.schemas.rota import (
    AvailableStaffRequestSchema,
    CancelOccurrenceSchema,
    CreateAssignmentSchema,
    EditAllSchema,
    EditFollowingSchema,
    EditOccurrenceSchema,
    PracticeGridRequestSchema,
    StaffContextEnriched,
    PracticeContext
)


class RotaService:
    """Wrapper service class around the RotaConnector SDK."""
    
    def __init__(
        self, 
        client_id: str, 
        client_secret: str, 
        base_url: Optional[str] = None,
        staff_provider: Optional[IResourceProvider] = None,
        practice_provider: Optional[IContextProvider] = None
    ):
        """
        Initialize the connector and optionally wire in your ORM Providers.
        """
        kwargs = {}
        if base_url:
            kwargs["base_url"] = base_url
            
        self.connector = RotaConnector(**kwargs)
        self.connector.set_credentials(client_id, client_secret)
        self.staff_provider = staff_provider
        self.practice_provider = practice_provider

    def check_health(self) -> Any:
        return self.connector.health()


    # ── Providers Helper ──────────────────────────────────────────────────────

    def get_assignment_contexts(self, staff_id: UUID, practice_id: UUID, target_date: Optional[date] = None) -> dict:
        """
        Queries the DB Providers for live capacity, slots, and required 
        hours to automatically hydrate assignment payloads without frontend intervention.
        """
        if not self.staff_provider or not self.practice_provider:
             raise ValueError("Both staff_provider and practice_provider must be initialized to auto-hydrate contexts.")
             
        # Ask Provider for Practice rules (e.g. 40 hours standard)
        practice_context = self.practice_provider.get_practice_context(practice_id)
        
        # Ask Provider for Staff capacity
        date_range = DateRangeFilter(start_date=target_date, end_date=target_date) if target_date else None
        staff_context = self.staff_provider.get_staff_context(staff_id, date_range=date_range)
        
        return {
            "staff_context": staff_context,
            "practice_context": practice_context
        }


    # ── Grid & Availability ───────────────────────────────────────────────────

    def get_practice_grid(self, payload: PracticeGridRequestSchema) -> Any:
        """
        Fetch the weekly practice-view grid schedule from the engine.
        Returns a timeline grouped by practice_id and date.
        """
        return self.connector.rota.practice_grid(payload)

    def get_staff_grid(self, week_start: date, role_id: UUID, staff_ids: Optional[str] = None, practice_id: Optional[UUID] = None) -> Any:
        """
        Fetch the weekly staff-view grid schedule from the engine.
        Returns a timeline grouped by staff_id and date.
        """
        return self.connector.rota.staff_grid(
            week_start=week_start, role_id=role_id, staff_ids=staff_ids, practice_id=practice_id
        )

    def get_available_staff(
        self, 
        practice_id: UUID, 
        target_date: date, 
        role_id: UUID, 
        payload: AvailableStaffRequestSchema
    ) -> Any:
        """
        *(Native)* Query the ROTA engine natively for real-time staff availability over a target date.
        
        The ROTA backend acts as a calculation engine. You manually push in all staff and 
        their individual working rules/hours, and the engine cross-references them against 
        existing allocations, returning exactly who can take the shift and how much capacity 
        they have left.

        Args:
            practice_id (UUID): The practice requesting staff.
            target_date (date): The exact date you want to evaluate availability.
            role_id (UUID): Role requirement.
            payload (AvailableStaffRequestSchema):
                Requires `staff_contexts` = List of `StaffContextEnriched`.

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

    def auto_get_available_staff(self, practice_id: UUID, target_date: date, role_id: UUID) -> Any:
        """
        *(Smart Helper)* Dynamically hydrates the entire AvailableStaffRequestSchema payload 
        by querying the injected `staff_provider` for all staff capacity contexts 
        assigned to the practice.
        
        This means no manual payload formatting is required to resolve availability!
        """
        if not self.staff_provider:
             raise ValueError("staff_provider is required for auto-hydration.")
             
        # Ask DB for all staff working contexts at this practice
        staff_list = self.staff_provider.list_staff_contexts(practice_id=practice_id)
        
        payload = AvailableStaffRequestSchema(staff_contexts=staff_list)
        return self.get_available_staff(practice_id, target_date, role_id, payload)


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
        *(Native)* Create a new ONE-OFF or RECURRING assignment natively. 
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


    def safe_create_assignment(self, payload: CreateAssignmentSchema) -> Any:
        """
        *(Smart Helper)* Safely validate your custom business logic before pushing the 
        assignment to the remote engine.
        
        Utilizes `practice_provider.validate_entity_in_context` to guarantee the 
        target staff member is legally allowed to work at the target practice based 
        on your internal database rules.
        """
        if self.practice_provider:
            is_member = self.practice_provider.validate_entity_in_context(
                staff_id=payload.staff_id, 
                practice_id=payload.practice_id
            )
            if not is_member:
                raise ValueError("Validation Failed: Staff member is not assigned to this context!")
                
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
                - staff_context, practice_context: Live quota contexts.
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
                - staff_context, practice_context: Live quota contexts.
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
