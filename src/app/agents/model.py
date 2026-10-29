from datetime import datetime, timezone
from typing import Any

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..shared.database import Base
from ..shared.registry import RegistryMixin, UnifiedResourceType
from ..shared.utils import UtcDateTime


class Agent(Base, RegistryMixin):
    __tablename__ = "agent"
    __registry_type__ = UnifiedResourceType.AGENT
    __table_args__ = (
        UniqueConstraint("tenant_uuid", "slug", name="uq_agent_tenant_slug"),
        Index("ix_agent_tenant_updated_at", "tenant_uuid", "updated_at"),
    )

    uuid: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
    )
    tenant_uuid: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tenant.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    owner_uuid: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("user.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(String, default="", nullable=False)
    workflow: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # Optimistic concurrency token for updates over the API.
    etag: Mapped[str] = mapped_column(String(64), default="", nullable=False)
