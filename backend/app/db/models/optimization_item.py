from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OptimizationItem(Base):
    __tablename__ = "optimization_items"

    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "resource_id",
            name="uq_optimization_items_run_resource",
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

    resource_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    service: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    env: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )

    owner: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    region: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    avg_cpu_utilization: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    avg_memory_utilization: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    avg_disk_utilization: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    avg_gpu_utilization: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    monthly_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    issue_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    recommended_action: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    estimated_monthly_saving: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0"),
    )

    risk_level: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )

    need_human_approval: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )