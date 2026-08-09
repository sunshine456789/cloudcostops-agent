from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.sql.sqltypes import JSON

from backend.app.db.models import (
    AgentRun,
    GeneratedReport,
    OptimizationItem,
    WorkflowStep,
)
from backend.app.db.session import SessionLocal
from backend.app.repositories.cloudcost_repository import (
    replace_optimization_items,
    replace_workflow_steps,
    save_agent_run,
    save_generated_report,
)


def _model_columns(model) -> dict[str, Any]:
    """
    获取 SQLAlchemy Model 当前真实字段。

    这样 Persistence Service 不会因为某个 ORM 模型
    多一个/少一个字段而直接崩掉。
    """
    return {
        column.name: column
        for column in model.__table__.columns
    }


def _normalize_value(column, value):
    """
    根据数据库字段类型处理 dict/list。

    JSON 字段直接保存 Python 对象；
    Text/String 字段则转 JSON 字符串。
    """

    if value is None:
        return None

    if isinstance(value, (dict, list)):
        if isinstance(column.type, JSON):
            return value

        return json.dumps(
            value,
            ensure_ascii=False,
        )

    return value


def _create_model(
    model,
    values: dict[str, Any],
    aliases: dict[str, list[str]] | None = None,
):
    """
    根据 ORM 当前实际字段动态创建对象。

    aliases 用来兼容：
    report_path -> path
    report_filename -> filename
    等命名差异。
    """

    aliases = aliases or {}

    columns = _model_columns(model)
    payload = {}

    for source_name, value in values.items():

        candidate_names = [
            source_name,
            *aliases.get(source_name, []),
        ]

        for target_name in candidate_names:

            if target_name not in columns:
                continue

            payload[target_name] = _normalize_value(
                columns[target_name],
                value,
            )

            break

    return model(**payload)


# ============================================================
# AgentRun
# ============================================================

def _build_agent_run(
    result: dict[str, Any],
) -> AgentRun:

    status = result.get(
        "status",
        "unknown",
    )

    values = {
        "run_id": result.get("run_id"),
        "status": status,
        "workflow_engine": result.get(
            "workflow_engine",
            "langgraph",
        ),
        "llm_model": result.get("llm_model"),
        "max_risk_level": result.get(
            "max_risk_level",
        ),
        "approval_required": result.get(
            "approval_required",
            False,
        ),
        "estimated_monthly_saving": result.get(
            "estimated_monthly_saving",
            0,
        ),
        "saving_rate": result.get(
            "saving_rate",
            0,
        ),
    }

    if status in {
        "completed",
        "rejected",
        "failed",
    }:
        values["completed_at"] = datetime.utcnow()

    return _create_model(
        AgentRun,
        values,
    )


# ============================================================
# WorkflowStep
# ============================================================

def _build_workflow_steps(
    result: dict[str, Any],
) -> list[WorkflowStep]:

    run_id = result.get("run_id")

    raw_steps = result.get(
        "workflow_steps",
        [],
    )

    objects = []

    for index, step in enumerate(
        raw_steps,
        start=1,
    ):

        if not isinstance(step, dict):
            continue

        values = {
            "run_id": run_id,
            "step_id": step.get(
                "step_id",
                index,
            ),
            "agent_name": step.get(
                "agent_name",
            ),
            "stage": step.get("stage"),
            "status": step.get("status"),
            "status_label": step.get(
                "status_label",
            ),
            "duration_ms": step.get(
                "duration_ms",
                0,
            ),
            "action": step.get("action"),
            "key_output": step.get(
                "key_output",
            ),
            "evidence": step.get(
                "evidence",
            ),
        }

        obj = _create_model(
            WorkflowStep,
            values,
            aliases={
                "evidence": [
                    "evidence_json",
                    "evidence_text",
                ],
            },
        )

        objects.append(obj)

    return objects


# ============================================================
# OptimizationItem
# ============================================================

def _build_optimization_items(
    result: dict[str, Any],
) -> list[OptimizationItem]:

    run_id = result.get("run_id")

    # 优先保存全部优化建议。
    # 如果当前 Graph 暂时只暴露 approval_items，
    # 则先用 approval_items。
    raw_items = (
        result.get("optimization_items")
        or result.get("recommendations")
        or result.get("approval_items")
        or []
    )

    objects = []

    for item in raw_items:

        if not isinstance(item, dict):
            continue

        values = {
            "run_id": run_id,

            "resource_id": item.get(
                "resource_id",
            ),

            "service": item.get(
                "service",
            ),

            "env": item.get(
                "env",
            ),

            "owner": item.get(
                "owner",
            ),

            "region": item.get(
                "region",
            ),

            "avg_cpu_utilization": item.get(
                "avg_cpu_utilization",
            ),

            "avg_memory_utilization": item.get(
                "avg_memory_utilization",
            ),

            "avg_disk_utilization": item.get(
                "avg_disk_utilization",
            ),

            "avg_gpu_utilization": item.get(
                "avg_gpu_utilization",
            ),

            "monthly_cost": item.get(
                "monthly_cost",
            ),

            "issue_type": item.get(
                "issue_type",
            ),

            "recommend_action": item.get(
                "recommend_action",
            ),

            "estimated_monthly_saving": item.get(
                "estimated_monthly_saving",
            ),

            "risk_level": item.get(
                "risk_level",
            ),

            "need_human_approval": item.get(
                "need_human_approval",
                False,
            ),

            "reason": item.get(
                "reason",
            ),
        }

        obj = _create_model(
            OptimizationItem,
            values,
            aliases={
                "recommend_action": [
                    "recommended_action",
                    "action",
                ],
            },
        )

        objects.append(obj)

    return objects


# ============================================================
# GeneratedReport
# ============================================================

def _build_report(
    result: dict[str, Any],
) -> GeneratedReport | None:

    report_id = result.get(
        "report_id",
    )

    if not report_id:
        return None

    values = {
        "report_id": report_id,
        "run_id": result.get(
            "run_id",
        ),
        "report_filename": result.get(
            "report_filename",
        ),
        "report_path": result.get(
            "report_path",
        ),
        "report_type": "cost_optimization",
    }

    return _create_model(
        GeneratedReport,
        values,
        aliases={
            "report_filename": [
                "filename",
            ],
            "report_path": [
                "path",
                "file_path",
            ],
        },
    )


# ============================================================
# Main Persistence Function
# ============================================================

def persist_agent_result(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    将一次 LangGraph 执行结果完整持久化。

    整个写入过程使用同一个数据库事务：

        AgentRun
        WorkflowStep
        OptimizationItem
        GeneratedReport

    任意一步失败则整体 rollback。
    """

    run_id = result.get("run_id")

    if not run_id:
        raise ValueError(
            "LangGraph result 缺少 run_id，"
            "无法进行数据库持久化。"
        )

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # 1. Agent Run
        # ----------------------------------------------------

        run = _build_agent_run(
            result
        )

        save_agent_run(
            db,
            run,
        )

        # ----------------------------------------------------
        # 2. Workflow Steps
        # ----------------------------------------------------

        workflow_steps = (
            _build_workflow_steps(
                result
            )
        )

        replace_workflow_steps(
            db,
            run_id,
            workflow_steps,
        )

        # ----------------------------------------------------
        # 3. Optimization Items
        # ----------------------------------------------------

        optimization_items = (
            _build_optimization_items(
                result
            )
        )

        replace_optimization_items(
            db,
            run_id,
            optimization_items,
        )

        # ----------------------------------------------------
        # 4. Generated Report
        # ----------------------------------------------------

        report = _build_report(
            result
        )

        if report is not None:
            save_generated_report(
                db,
                report,
            )

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        db.commit()

        return {
            "success": True,
            "run_id": run_id,
            "workflow_step_count": len(
                workflow_steps
            ),
            "optimization_item_count": len(
                optimization_items
            ),
            "report_saved": (
                report is not None
            ),
        }

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()