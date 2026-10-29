from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.shared.database import Base
from src.app.shared.registry import AutoUUIDMixin, new_uuid
from src.app.shared.utils import UtcDateTime

if TYPE_CHECKING:
    from src.app.chat.model import Thread


class User(Base, AutoUUIDMixin):
    __tablename__ = "user"

    uuid: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=new_uuid,
        nullable=False,
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
    name: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(255), unique=True)

    threads: Mapped[list["Thread"]] = relationship(
        "Thread",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
