from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, PrivateAttr

class RecordsUnknownKeys(BaseModel):
    _unknown_keys: tuple[str, ...] = PrivateAttr(default=())
    _doubled_fields: tuple[str, ...] = PrivateAttr(default=())


class AgentBase(BaseModel):
    name: str = Field(...)
    slug: str = Field(...)
    description: str = Field(...)

class AgentResponse(AgentBase):
    uuid: str
    etag: str = Field(
        default="",
    )
    owner_uuid: str | None = Field(default=None, description="owner uuid")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class AgentWorkflow(RecordsUnknownKeys):
    pass
