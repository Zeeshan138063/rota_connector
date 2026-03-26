import uuid
from rota_connector.schemas.project import ProjectCreateSchema

def test_register_project(connector, httpx_mock):
    payload = ProjectCreateSchema(
        project_name="Test Project",
        slug="test-project"
    )

    httpx_mock.add_response(
        method="POST",
        url=f"{connector._base_client.base_url}/api/v1/projects/register",
        json={"data": {"project_id": str(uuid.uuid4()), "slug": "test-project"}}
    )

    result = connector.projects.register_project(payload)
    assert result["slug"] == "test-project"

def test_rotate_secret(connector, httpx_mock):
    project_id = uuid.uuid4()
    
    httpx_mock.add_response(
        method="POST",
        url=f"{connector._base_client.base_url}/api/v1/projects/{project_id}/rotate-secret",
        json={"data": {"client_secret": "new-secret"}}
    )

    result = connector.projects.rotate_secret(project_id)
    assert result["client_secret"] == "new-secret"
