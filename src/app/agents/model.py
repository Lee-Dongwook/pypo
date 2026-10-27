from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..shared.utils import UtcDateTime
from ..shared.database import Base
from ..shared.registry import UnifiedResourceType, RegistryMixin

class Agent(Base, RegistryMixin):
    __tablename__ = "agent"
    __registry_type__ = UnifiedResourceType.AGENT

    uuid: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )
    name: Mapped[str] = mapped_column(
        String,
    )
    slug: Mapped[str] = mapped_column(
        String,
    )
    type: Mapped[str] = mapped_column(
        String,
    )
    description: Mapped[str] = mapped_column(String, default="")
