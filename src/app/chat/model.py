from datetime import datetime
from time import timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.app.shared.registry import new_uuid
from src.app.shared.utils import UtcDateTime

from ..shared.database import Base

if TYPE_CHECKING:
    from ..user.model import User

class Thread(Base):
    __tablename__ = "chat_thread"
    __table_args__ = (Index("ix_thread_user_updated_at", "user_uuid", text("updated_at DESC"), text("uuid DESC")),)
    uuid: Mapped[str] = mapped_column(UUID(as_uuid=False), default=new_uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.now(timezone.utc))
    title: Mapped[str] = mapped_column(String, default="")
    agent_uuid: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    user_uuid : Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("user.uuid"))
    user: Mapped["User"] = relationship("User", back_populates="chat_thread")

