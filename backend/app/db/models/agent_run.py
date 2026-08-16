from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class AgentRun(Base):
    """
    CloudCostOps Agent 单次工作流运行记录。

    保存：
    - 工作流状态
    - LLM 信息
    - 风险等级
    - HITL 人工审批信息
    - 成本优化收益
    - 输入文件
    - 总执行时间
    """

    __tablename__ = "agent_runs"

    # =========================================================
    # Primary Key
    # =========================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # =========================================================
    # Run Identity
    # =========================================================

    run_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    # =========================================================
    # Workflow
    # =========================================================

    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="running",
        index=True,
    )

    workflow_engine: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    # =========================================================
    # LLM
    # =========================================================

    llm_enabled: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    llm_model: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    llm_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # =========================================================
    # Risk
    # =========================================================

    max_risk_level: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    # =========================================================
    # Human Approval
    # =========================================================

    approval_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    approval_decision: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    approval_operator: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    approval_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    approved_scope: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    # =========================================================
    # Cost Optimization
    # =========================================================

    estimated_monthly_saving: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=0.0,
    )

    saving_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=0.0,
    )

    # =========================================================
    # Input Files
    # =========================================================

    billing_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    utilization_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # =========================================================
    # Performance
    # =========================================================

    total_elapsed_time: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # =========================================================
    # Time
    # =========================================================

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )