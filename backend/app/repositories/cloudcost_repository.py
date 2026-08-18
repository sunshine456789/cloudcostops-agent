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


# ============================================================
# AgentRun
# ============================================================

def get_agent_run(
    db: Session,
    run_id: str,
) -> AgentRun | None:
    """
    根据 run_id 查询单次 Agent Run。
    """

    stmt = (
        select(
            AgentRun
        )
        .where(
            AgentRun.run_id
            == run_id
        )
    )

    return db.scalar(
        stmt
    )


def _copy_agent_run_fields(
    existing: AgentRun,
    incoming: AgentRun,
) -> None:
    """
    将 incoming AgentRun 的最新业务字段同步到已有记录。

    关键设计：

    1. 不再写死具体业务字段名称。
    2. 直接读取 SQLAlchemy 当前真实 ORM 映射字段。
    3. 兼容不同版本 AgentRun 模型，例如：

        llm_enabled
        use_llm
        is_llm_enabled

        billing_filename
        billing_file_name
        billing_file

        utilization_filename
        utilization_file_name
        utilization_file

        total_elapsed_time
        elapsed_time
        elapsed_time_s

    4. incoming 为 None 时不覆盖旧值。

       CloudCostOps 一个 Run 通常至少持久化两次：

           第一次：
               optimization-plan
               ->
               pending_approval

           第二次：
               approval-decision
               ->
               completed / rejected

       Resume 阶段未必会重新返回第一阶段全部字段。

       因此不能使用 None 把数据库已有字段清空。

    5. False 和 0 都是合法值，必须正常保存。
    """

    # --------------------------------------------------------
    # 不应在 Upsert 时修改的字段
    # --------------------------------------------------------

    skip_fields = {
        "id",
        "run_id",
        "created_at",
        "updated_at",
    }

    # --------------------------------------------------------
    # SQLAlchemy Mapper
    #
    # 这里读取 incoming 当前真实 ORM 字段，
    # 不再维护 candidate_fields。
    # --------------------------------------------------------

    mapper = incoming.__mapper__

    for attr in mapper.column_attrs:

        field_name = attr.key

        # ----------------------------------------------------
        # 跳过主键、run_id 和自动时间字段
        # ----------------------------------------------------

        if field_name in skip_fields:
            continue

        # ----------------------------------------------------
        # ORM 兼容保护
        # ----------------------------------------------------

        if not hasattr(
            existing,
            field_name,
        ):
            continue

        if not hasattr(
            incoming,
            field_name,
        ):
            continue

        value = getattr(
            incoming,
            field_name,
            None,
        )

        # ----------------------------------------------------
        # None 表示当前阶段没有携带该数据。
        #
        # 不允许用 None 覆盖第一阶段已经存好的值。
        #
        # 注意：
        #
        # False
        # 0
        # 0.0
        # ""
        #
        # 都不是 None，因此仍然会正常更新。
        # ----------------------------------------------------

        if value is None:
            continue

        setattr(
            existing,
            field_name,
            value,
        )


def save_agent_run(
    db: Session,
    run: AgentRun,
) -> AgentRun:
    """
    Upsert AgentRun。

    不存在：
        INSERT

    已存在：
        UPDATE
    """

    existing = (
        get_agent_run(
            db=db,
            run_id=run.run_id,
        )
    )

    if existing is None:

        db.add(
            run
        )

        db.flush()

        return run

    # --------------------------------------------------------
    # Existing Run
    # --------------------------------------------------------

    _copy_agent_run_fields(
        existing=existing,
        incoming=run,
    )

    db.flush()

    return existing


# ============================================================
# Workflow Steps
# ============================================================

def replace_workflow_steps(
    db: Session,
    run_id: str,
    steps: Sequence[WorkflowStep],
) -> None:
    """
    使用当前最新 workflow_steps
    替换数据库中该 run_id 对应的旧步骤。

    原因：

    pending_approval 阶段：
        workflow_steps 可能只有 6 步

    approve 后：
        workflow_steps 可能变成 7 步

    因此直接 replace 比逐条 update 更简单可靠。
    """

    db.execute(
        delete(
            WorkflowStep
        ).where(
            WorkflowStep.run_id
            == run_id
        )
    )

    if steps:
        db.add_all(
            list(
                steps
            )
        )

    db.flush()


# ============================================================
# Optimization Items
# ============================================================

def replace_optimization_items(
    db: Session,
    run_id: str,
    items: Sequence[OptimizationItem],
) -> None:
    """
    替换该 run_id 对应的最新优化建议。
    """

    db.execute(
        delete(
            OptimizationItem
        ).where(
            OptimizationItem.run_id
            == run_id
        )
    )

    if items:
        db.add_all(
            list(
                items
            )
        )

    db.flush()


# ============================================================
# Approval Decisions
# ============================================================

def add_approval_decision(
    db: Session,
    approval: ApprovalDecision,
) -> ApprovalDecision:
    """
    添加一条人工审批历史。

    与 AgentRun 不同：

    AgentRun
        保存当前最终状态

    ApprovalDecision
        保存审批事件历史

    因此这里使用 INSERT，
    而不是覆盖旧审批记录。
    """

    db.add(
        approval
    )

    db.flush()

    return approval


def list_approval_history(
    db: Session,
    run_id: str,
) -> list[ApprovalDecision]:
    """
    查询某次 Agent Run 的全部审批历史。
    """

    stmt = (
        select(
            ApprovalDecision
        )
        .where(
            ApprovalDecision.run_id
            == run_id
        )
        .order_by(
            ApprovalDecision.created_at.asc()
        )
    )

    return list(
        db.scalars(
            stmt
        ).all()
    )


# ============================================================
# Generated Reports
# ============================================================

def save_generated_report(
    db: Session,
    report: GeneratedReport,
) -> GeneratedReport:
    """
    保存报告记录。

    report_id 已存在时更新，
    否则插入。
    """

    stmt = (
        select(
            GeneratedReport
        )
        .where(
            GeneratedReport.report_id
            == report.report_id
        )
    )

    existing = (
        db.scalar(
            stmt
        )
    )

    if existing is None:

        db.add(
            report
        )

        db.flush()

        return report

    # --------------------------------------------------------
    # ORM 兼容
    # --------------------------------------------------------
    #
    # 某些版本模型可能使用：
    #
    # filename
    # path
    #
    # 也可能使用：
    #
    # file_path
    #
    # --------------------------------------------------------

    for field_name in (
        "filename",
        "path",
        "file_path",
        "report_type",
    ):

        if not hasattr(
            existing,
            field_name,
        ):
            continue

        if not hasattr(
            report,
            field_name,
        ):
            continue

        value = getattr(
            report,
            field_name,
        )

        if value is not None:
            setattr(
                existing,
                field_name,
                value,
            )

    db.flush()

    return existing


# ============================================================
# Agent Run Query
# ============================================================

def list_agent_runs(
    db: Session,
    *,
    limit: int = 50,
) -> list[AgentRun]:
    """
    查询最近的 Agent Run。
    """

    stmt = (
        select(
            AgentRun
        )
        .order_by(
            AgentRun.created_at.desc()
        )
        .limit(
            limit
        )
    )

    return list(
        db.scalars(
            stmt
        ).all()
    )


def list_pending_runs(
    db: Session,
    *,
    limit: int = 50,
) -> list[AgentRun]:
    """
    查询所有等待人工审批的 Agent Run。
    """

    stmt = (
        select(
            AgentRun
        )
        .where(
            AgentRun.status
            == "pending_approval"
        )
        .order_by(
            AgentRun.created_at.desc()
        )
        .limit(
            limit
        )
    )

    return list(
        db.scalars(
            stmt
        ).all()
    )