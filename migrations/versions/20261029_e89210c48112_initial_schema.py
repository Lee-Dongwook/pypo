"""initial schema

Revision ID: e89210c48112
Revises:
Create Date: 2026-10-29 20:37:07.656155

Creates the base tables: tenant, user, agent, chat_thread, chat_message.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e89210c48112"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "tenant",
        sa.Column("uuid", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=63), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "user",
        sa.Column("uuid", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=30), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "agent",
        sa.Column("uuid", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("tenant_uuid", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("owner_uuid", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("workflow", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("etag", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["owner_uuid"], ["user.uuid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_uuid"], ["tenant.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("tenant_uuid", "slug", name="uq_agent_tenant_slug"),
    )
    op.create_index("ix_agent_tenant_updated_at", "agent", ["tenant_uuid", "updated_at"], unique=False)
    op.create_table(
        "chat_thread",
        sa.Column("uuid", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("agent_uuid", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("user_uuid", postgresql.UUID(as_uuid=False), nullable=False),
        sa.ForeignKeyConstraint(["agent_uuid"], ["agent.uuid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_uuid"], ["user.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(
        "ix_thread_user_updated_at",
        "chat_thread",
        ["user_uuid", sa.literal_column("updated_at DESC"), sa.literal_column("uuid DESC")],
        unique=False,
    )
    op.create_table(
        "chat_message",
        sa.Column("uuid", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("thread_uuid", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thread_uuid"], ["chat_thread.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(
        "ix_message_thread_created_at",
        "chat_message",
        ["thread_uuid", "created_at", "uuid"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_message_thread_created_at", table_name="chat_message")
    op.drop_table("chat_message")
    op.drop_index("ix_thread_user_updated_at", table_name="chat_thread")
    op.drop_table("chat_thread")
    op.drop_index("ix_agent_tenant_updated_at", table_name="agent")
    op.drop_table("agent")
    op.drop_table("user")
    op.drop_table("tenant")
