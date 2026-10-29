from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.shared.database import Base
from src.app.shared.registry import AutoUUIDMixin, new_uuid
from src.app.shared.utils import UtcDateTime

if TYPE_CHECKING:
    from src.app.user.model import User


class Thread(Base, AutoUUIDMixin):
    __tablename__ = "chat_thread"
    __table_args__ = (
        Index(
            "ix_thread_user_updated_at",
            "user_uuid",
            text("updated_at DESC"),
            text("uuid DESC"),
        ),
    )

    uuid: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        default=new_uuid,
        primary_key=True,
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
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    agent_uuid: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("agent.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    user_uuid: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("user.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="threads")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by=lambda: (Message.created_at, Message.uuid),
    )


class Message(Base, AutoUUIDMixin):
    __tablename__ = "chat_message"
    __table_args__ = (
        Index("ix_message_thread_created_at", "thread_uuid", "created_at", "uuid"),
    )

    uuid: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        default=new_uuid,
        primary_key=True,
    )
    thread_uuid: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("chat_thread.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    thread: Mapped["Thread"] = relationship("Thread", back_populates="messages")
