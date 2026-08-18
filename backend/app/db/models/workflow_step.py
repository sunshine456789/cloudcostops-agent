from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "step_id",
            name="uq_workflow_steps_run_step",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_runs.run_id"),
        nullable=False,
        index=True,
    )

    step_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    agent_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    stage: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    status_label: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    duration_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    action: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    key_output: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    evidence_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )