from typing import Any
from uuid import UUID

from rota_connector.base_client import BaseClient
from rota_connector.schemas.project import ProjectCreateSchema, ProjectOutSchema


class ProjectsAPI:
    """Client for projects endpoints."""

    def __init__(self, client: BaseClient, version: str = "v1"):
        self.client = client
        self.version = version

    def _base(self) -> str:
        return f"/api/{self.version}/projects"

    def register_project(self, payload: ProjectCreateSchema) -> Any:
        """Register a new project in the system."""
        response = self.client.post(f"{self._base()}/register/", json=payload.model_dump(mode="json"))
        return response.get("data") if response and "data" in response else response

    def rotate_secret(self, project_id: UUID) -> Any:
        """Rotate client_secret for a project."""
        response = self.client.post(f"{self._base()}/{project_id}/rotate-secret")
        return response.get("data") if response and "data" in response else response
