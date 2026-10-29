from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class RecordsUnknownKeys(BaseModel):
    _unknown_keys: tuple[str, ...] = PrivateAttr(default=())
    _doubled_fields: tuple[str, ...] = PrivateAttr(default=())


class AgentBase(BaseModel):
    name: str = Field(...)
    slug: str = Field(...)
    description: str = Field(...)


class AgentResponse(AgentBase):
    uuid: str
    tenant_uuid: str
    type: str
    workflow: dict[str, Any] = Field(default_factory=dict)
    etag: str = Field(
        default="",
    )
    owner_uuid: str | None = Field(default=None, description="owner uuid")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AgentWorkflow(RecordsUnknownKeys):
    pass
