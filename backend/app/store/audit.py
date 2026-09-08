"""Audit trail — every analysis run and every flag it raised, with the
reason, rule version, and timestamp. AML decisions must be reviewable
after the fact; this is that record."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..models.schemas import ExecutionPlan, Flag
from .db import Base, get_session

RULE_VERSION = "0.1.0"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    query: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(64))
    plan_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    flags: Mapped[list["AuditFlag"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class AuditFlag(Base):
    __tablename__ = "audit_flags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("audit_runs.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(16))
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    pattern: Mapped[str] = mapped_column(String(32))
    risk_level: Mapped[str] = mapped_column(String(8))
    score: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)
    escalation: Mapped[str] = mapped_column(String(16))
    rule_version: Mapped[str] = mapped_column(String(16), default=RULE_VERSION)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    run: Mapped[AuditRun] = relationship(back_populates="flags")


def record_run(plan: ExecutionPlan, flags: list[Flag]) -> str:
    """Persist a run + its flags; returns the run id."""
    run_id = str(uuid.uuid4())
    with get_session() as session:
        session.add(
            AuditRun(
                id=run_id,
                query=plan.query,
                intent=plan.intent,
                plan_json=plan.model_dump_json(),
            )
        )
        for flag in flags:
            session.add(
                AuditFlag(
                    id=str(uuid.uuid4()),
                    run_id=run_id,
                    entity_type=flag.entity_type,
                    entity_id=flag.entity_id,
                    pattern=flag.pattern.value,
                    risk_level=flag.risk_level.value,
                    score=flag.score,
                    reason=flag.reason,
                    escalation=flag.escalation.value,
                )
            )
        session.commit()
    return run_id


def flags_for_entity(entity_id: str) -> list[AuditFlag]:
    """Existing flags for an account/customer — used by single-entity lookups."""
    with get_session() as session:
        return (
            session.query(AuditFlag)
            .filter(AuditFlag.entity_id == entity_id)
            .order_by(AuditFlag.created_at.desc())
            .all()
        )
