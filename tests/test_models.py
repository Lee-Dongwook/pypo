from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import src.app.models  # noqa: F401  # registers every table on Base.metadata
from src.app.agents.graph.utils import _bakes_an_identity, _build_copy
from src.app.agents.model import Agent
from src.app.agents.schemas import AgentResponse
from src.app.shared.database import Base
from src.app.tenant.model import Tenant


def _agent(**overrides: object) -> Agent:
    fields: dict[str, object] = {
        "uuid": "01a18700-0000-7000-8000-000000000000",
        "tenant_uuid": "01a18700-0000-7000-8000-000000000001",
        "name": "risk analyst",
        "slug": "risk-analyst",
        "type": "assistant",
        "description": "answers supplier risk questions",
        "workflow": {},
        "etag": "v1",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    fields.update(overrides)
    return Agent(**fields)


def test_all_models_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "agent",
        "chat_message",
        "chat_thread",
        "tenant",
        "user",
    }


def test_agent_columns_cover_tenant_owner_and_workflow() -> None:
    columns = Agent.__table__.c

    assert columns.tenant_uuid.nullable is False
    assert columns.owner_uuid.nullable is True
    assert columns.workflow.nullable is False
    assert isinstance(columns.workflow.type, postgresql.JSONB)


def test_agent_datetime_defaults_are_callables() -> None:
    for name in ("created_at", "updated_at"):
        default = Agent.__table__.c[name].default
        assert default is not None
        assert default.is_callable, f"{name} default is frozen at import time"


def test_agent_slug_is_unique_per_tenant() -> None:
    uniques = {
        tuple(sorted(constraint.columns.keys()))
        for constraint in Agent.__table__.constraints
        if isinstance(constraint, sa.UniqueConstraint)
    }
    assert ("slug", "tenant_uuid") in uniques


def test_agent_foreign_keys() -> None:
    foreign_keys = {
        fk.parent.name: (fk.target_fullname, fk.ondelete) for fk in Agent.__table__.foreign_keys
    }

    assert foreign_keys["tenant_uuid"] == ("tenant.uuid", "CASCADE")
    assert foreign_keys["owner_uuid"] == ("user.uuid", "SET NULL")


def test_agent_ddl_compiles_for_postgres() -> None:
    ddl = str(CreateTable(Agent.__table__).compile(dialect=postgresql.dialect()))

    assert "JSONB" in ddl
    assert "tenant_uuid" in ddl
    assert "uq_agent_tenant_slug" in ddl


def test_agent_uuid_is_generated_on_construction() -> None:
    first = Agent(tenant_uuid="tenant", name="a", slug="a", type="assistant")
    second = Agent(tenant_uuid="tenant", name="b", slug="b", type="assistant")

    assert first.uuid != second.uuid
    assert len(first.uuid) == 36


def test_tenant_slug_is_globally_unique() -> None:
    assert Tenant.__table__.c.slug.unique is True


def test_agent_response_exposes_workflow_and_tenant() -> None:
    agent = _agent(workflow={"nodes": [{"id": "plan", "type": "llm"}]})

    response = AgentResponse.model_validate(agent, from_attributes=True)

    assert response.tenant_uuid == agent.tenant_uuid
    assert response.workflow == {"nodes": [{"id": "plan", "type": "llm"}]}


def test_identity_agents_are_detected_by_empty_workflow() -> None:
    assert _bakes_an_identity(_agent(workflow={})) is True
    assert _bakes_an_identity(_agent(workflow={"nodes": []})) is False


def test_build_copy_detaches_the_orm_object() -> None:
    original = _agent(workflow={"nodes": []})

    clone = _build_copy(original)

    assert clone is not original
    assert clone.uuid == original.uuid
    assert clone.workflow == original.workflow
