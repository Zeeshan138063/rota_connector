from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreateSchema(BaseModel):
    project_name: str = Field(..., max_length=255, examples=["Acme Corp Staffing"])
    slug: Optional[str] = Field(None, max_length=100, examples=["acme-corp"])
    project_description: Optional[str] = Field(
        None, examples=["Internal staffing system"]
    )
    domain_type: Optional[str] = Field(None, max_length=50, examples=["healthcare"])
    webhook_url: Optional[str] = Field(
        None, max_length=500, examples=["https://api.rota.com/webhook"]
    )


class ProjectOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    project_id: UUID
    project_name: str
    slug: str
    client_id: str
    client_secret: str = Field(
        ...,
        description="Plaintext secret. Save this immediately, it will not be shown again.",
    )
    status: str
    is_active: bool
    created_at: datetime
