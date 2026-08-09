from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.db.models import (
    AgentRun,
    ApprovalDecision,
    GeneratedReport,
    OptimizationItem,
    WorkflowStep,
)


def get_agent_run(
    db: Session,
    run_id: str,
) -> AgentRun | None:
    stmt = select(AgentRun).where(
        AgentRun.run_id == run_id
    )
    return db.scalar(stmt)


def save_agent_run(
    db: Session,
    run: AgentRun,
) -> AgentRun:
    existing = get_agent_run(
        db=db,
        run_id=run.run_id,
    )

    if existing is None:
        db.add(run)
        db.flush()
        return run

    existing.status = run.status
    existing.workflow_engine = run.workflow_engine
    existing.llm_model = run.llm_model
    existing.max_risk_level = run.max_risk_level
    existing.approval_required = run.approval_required
    existing.estimated_monthly_saving = run.estimated_monthly_saving
    existing.saving_rate = run.saving_rate

    if run.completed_at is not None:
        existing.completed_at = run.completed_at

    db.flush()
    return existing


def replace_workflow_steps(
    db: Session,
    run_id: str,
    steps: Sequence[WorkflowStep],
) -> None:
    db.execute(
        delete(WorkflowStep).where(
            WorkflowStep.run_id == run_id
        )
    )

    if steps:
        db.add_all(list(steps))

    db.flush()


def replace_optimization_items(
    db: Session,
    run_id: str,
    items: Sequence[OptimizationItem],
) -> None:
    db.execute(
        delete(OptimizationItem).where(
            OptimizationItem.run_id == run_id
        )
    )

    if items:
        db.add_all(list(items))

    db.flush()


def add_approval_decision(
    db: Session,
    approval: ApprovalDecision,
) -> ApprovalDecision:
    db.add(approval)
    db.flush()
    return approval


def list_approval_history(
    db: Session,
    run_id: str,
) -> list[ApprovalDecision]:
    stmt = (
        select(ApprovalDecision)
        .where(
            ApprovalDecision.run_id == run_id
        )
        .order_by(
            ApprovalDecision.created_at.asc()
        )
    )

    return list(db.scalars(stmt).all())


def save_generated_report(
    db: Session,
    report: GeneratedReport,
) -> GeneratedReport:
    stmt = select(GeneratedReport).where(
        GeneratedReport.report_id == report.report_id
    )

    existing = db.scalar(stmt)

    if existing is None:
        db.add(report)
        db.flush()
        return report

    existing.filename = report.filename
    existing.path = report.path
    existing.report_type = report.report_type

    db.flush()
    return existing


def list_agent_runs(
    db: Session,
    *,
    limit: int = 50,
) -> list[AgentRun]:
    stmt = (
        select(AgentRun)
        .order_by(
            AgentRun.created_at.desc()
        )
        .limit(limit)
    )

    return list(db.scalars(stmt).all())


def list_pending_runs(
    db: Session,
    *,
    limit: int = 50,
) -> list[AgentRun]:
    stmt = (
        select(AgentRun)
        .where(
            AgentRun.status == "pending_approval"
        )
        .order_by(
            AgentRun.created_at.desc()
        )
        .limit(limit)
    )

    return list(db.scalars(stmt).all())