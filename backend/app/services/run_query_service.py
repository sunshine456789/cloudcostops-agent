from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.orm import Session

from backend.app.db.models import (
    AgentRun,
    WorkflowStep,
    OptimizationItem,
    ApprovalDecision,
    GeneratedReport,
)


# ============================================================
# 基础工具
# ============================================================

def _to_json_safe(value: Any) -> Any:
    """
    将数据库字段转换成适合 FastAPI JSON 返回的值。
    """

    if value is None:
        return None

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    return value


def _try_parse_json(value: Any) -> Any:
    """
    某些字段可能以 JSON 字符串存储在数据库中。
    如果能解析就转换成 Python 对象，否则原样返回。
    """

    if not isinstance(value, str):
        return value

    text = value.strip()

    if not text:
        return value

    if not (
        (text.startswith("{") and text.endswith("}"))
        or (text.startswith("[") and text.endswith("]"))
    ):
        return value

    try:
        return json.loads(text)
    except Exception:
        return value


def _model_to_dict(obj: Any) -> dict[str, Any]:
    """
    SQLAlchemy ORM 对象 -> dict

    这样做的好处是：
    不需要在这里手写每一个数据库字段，
    后续 ORM 模型新增字段时也不容易报错。
    """

    if obj is None:
        return {}

    result: dict[str, Any] = {}

    mapper = sqlalchemy_inspect(obj).mapper

    for attr in mapper.column_attrs:
        key = attr.key
        value = getattr(obj, key, None)

        value = _to_json_safe(value)
        value = _try_parse_json(value)

        result[key] = value

    return result


def _pick(
    data: dict[str, Any],
    *names: str,
    default: Any = None,
) -> Any:
    """
    兼容不同版本数据库字段命名。

    例如：
    report_filename / filename
    total_elapsed_time / elapsed_time
    """

    for name in names:
        if name in data and data[name] is not None:
            return data[name]

    return default


def _query_by_run_id(
    db: Session,
    model: Any,
    run_id: str,
) -> list[Any]:
    """
    查询某个 run_id 对应的子表记录。
    """

    if not hasattr(model, "run_id"):
        return []

    query = db.query(model).filter(
        getattr(model, "run_id") == run_id
    )

    # 尽量保持工作流执行顺序
    if hasattr(model, "step_id"):
        query = query.order_by(getattr(model, "step_id").asc())

    elif hasattr(model, "created_at"):
        query = query.order_by(getattr(model, "created_at").asc())

    elif hasattr(model, "id"):
        query = query.order_by(getattr(model, "id").asc())

    return query.all()


# ============================================================
# 数据转换
# ============================================================

def _build_run_list_item(run: AgentRun) -> dict[str, Any]:
    data = _model_to_dict(run)

    return {
        "run_id": _pick(data, "run_id", default=""),

        "status": _pick(data, "status"),
        "workflow_engine": _pick(
            data,
            "workflow_engine",
            default="langgraph",
        ),

        "approval_required": bool(
            _pick(
                data,
                "approval_required",
                default=False,
            )
        ),

        "max_risk_level": _pick(
            data,
            "max_risk_level",
        ),

        "approval_decision": _pick(
            data,
            "approval_decision",
        ),

        "approval_operator": _pick(
            data,
            "approval_operator",
        ),

        "approved_scope": _pick(
            data,
            "approved_scope",
        ),

        "estimated_monthly_saving": _pick(
            data,
            "estimated_monthly_saving",
        ),

        "saving_rate": _pick(
            data,
            "saving_rate",
        ),

        "billing_filename": _pick(
            data,
            "billing_filename",
        ),

        "utilization_filename": _pick(
            data,
            "utilization_filename",
        ),

        "total_elapsed_time": _pick(
            data,
            "total_elapsed_time",
            "elapsed_time",
        ),

        "created_at": _pick(
            data,
            "created_at",
        ),

        "updated_at": _pick(
            data,
            "updated_at",
        ),
    }


def _build_workflow_step(
    obj: WorkflowStep,
) -> dict[str, Any]:
    data = _model_to_dict(obj)

    return {
        "step_id": _pick(
            data,
            "step_id",
            "sequence_no",
            "id",
        ),

        "agent_name": _pick(
            data,
            "agent_name",
        ),

        "stage": _pick(
            data,
            "stage",
        ),

        "status": _pick(
            data,
            "status",
        ),

        "status_label": _pick(
            data,
            "status_label",
        ),

        "duration_ms": _pick(
            data,
            "duration_ms",
            default=0,
        ),

        "action": _pick(
            data,
            "action",
        ),

        "key_output": _pick(
            data,
            "key_output",
        ),

        "evidence": _pick(
            data,
            "evidence",
        ),
    }


def _build_optimization_item(
    obj: OptimizationItem,
) -> dict[str, Any]:
    data = _model_to_dict(obj)

    return {
        "resource_id": _pick(
            data,
            "resource_id",
        ),

        "service": _pick(
            data,
            "service",
        ),

        "env": _pick(
            data,
            "env",
            "environment",
        ),

        "owner": _pick(
            data,
            "owner",
        ),

        "region": _pick(
            data,
            "region",
        ),

        "avg_cpu_utilization": _pick(
            data,
            "avg_cpu_utilization",
        ),

        "avg_memory_utilization": _pick(
            data,
            "avg_memory_utilization",
        ),

        "avg_disk_utilization": _pick(
            data,
            "avg_disk_utilization",
        ),

        "avg_gpu_utilization": _pick(
            data,
            "avg_gpu_utilization",
        ),

        "monthly_cost": _pick(
            data,
            "monthly_cost",
        ),

        "issue_type": _pick(
            data,
            "issue_type",
        ),

        "recommend_action": _pick(
            data,
            "recommend_action",
            "recommended_action",
        ),

        "estimated_monthly_saving": _pick(
            data,
            "estimated_monthly_saving",
        ),

        "risk_level": _pick(
            data,
            "risk_level",
        ),

        "need_human_approval": bool(
            _pick(
                data,
                "need_human_approval",
                default=False,
            )
        ),

        "reason": _pick(
            data,
            "reason",
        ),
    }


def _build_approval(
    obj: ApprovalDecision,
) -> dict[str, Any]:
    data = _model_to_dict(obj)

    return {
        "decision": _pick(
            data,
            "decision",
            "approval_decision",
        ),

        "operator": _pick(
            data,
            "operator",
            "approval_operator",
        ),

        "comment": _pick(
            data,
            "comment",
        ),

        "approved_scope": _pick(
            data,
            "approved_scope",
        ),

        "created_at": _pick(
            data,
            "created_at",
        ),
    }


def _build_report(
    obj: GeneratedReport,
) -> dict[str, Any]:
    data = _model_to_dict(obj)

    return {
        "report_id": _pick(
            data,
            "report_id",
        ),

        "report_filename": _pick(
            data,
            "report_filename",
            "filename",
        ),

        "report_path": _pick(
            data,
            "report_path",
            "path",
        ),

        "report_saved": _pick(
            data,
            "report_saved",
            "saved",
            default=True,
        ),

        "created_at": _pick(
            data,
            "created_at",
        ),
    }


# ============================================================
# 1. 历史 Agent Run 列表
# ============================================================

def list_agent_runs(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    approval_required: Optional[bool] = None,
) -> dict[str, Any]:

    page = max(page, 1)
    page_size = max(1, min(page_size, 100))

    query = db.query(AgentRun)

    # ---------- 状态过滤 ----------
    if status:
        if hasattr(AgentRun, "status"):
            query = query.filter(
                AgentRun.status == status
            )

    # ---------- 是否需要人工审批 ----------
    if approval_required is not None:
        if hasattr(AgentRun, "approval_required"):
            query = query.filter(
                AgentRun.approval_required
                == approval_required
            )

    total = query.count()

    # ---------- 排序 ----------
    if hasattr(AgentRun, "created_at"):
        query = query.order_by(
            AgentRun.created_at.desc()
        )

    elif hasattr(AgentRun, "id"):
        query = query.order_by(
            AgentRun.id.desc()
        )

    offset = (page - 1) * page_size

    rows = (
        query
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return {
        "success": True,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            _build_run_list_item(row)
            for row in rows
        ],
    }


# ============================================================
# 2. 单次 Agent Run 完整详情
# ============================================================

def get_agent_run_detail(
    db: Session,
    run_id: str,
) -> Optional[dict[str, Any]]:

    run = (
        db.query(AgentRun)
        .filter(AgentRun.run_id == run_id)
        .first()
    )

    if run is None:
        return None

    run_data = _model_to_dict(run)

    # ---------- 子表 ----------
    workflow_rows = _query_by_run_id(
        db,
        WorkflowStep,
        run_id,
    )

    optimization_rows = _query_by_run_id(
        db,
        OptimizationItem,
        run_id,
    )

    approval_rows = _query_by_run_id(
        db,
        ApprovalDecision,
        run_id,
    )

    report_rows = _query_by_run_id(
        db,
        GeneratedReport,
        run_id,
    )

    return {
        "success": True,

        "run_id": run_id,

        "status": _pick(
            run_data,
            "status",
        ),

        "workflow_engine": _pick(
            run_data,
            "workflow_engine",
            default="langgraph",
        ),

        # ====================================================
        # LLM
        # ====================================================

        "llm_enabled": _pick(
            run_data,
            "llm_enabled",
        ),

        "llm_model": _pick(
            run_data,
            "llm_model",
        ),

        "llm_error": _pick(
            run_data,
            "llm_error",
        ),

        # ====================================================
        # 输入文件
        # ====================================================

        "billing_filename": _pick(
            run_data,
            "billing_filename",
        ),

        "utilization_filename": _pick(
            run_data,
            "utilization_filename",
        ),

        # ====================================================
        # 成本优化结果
        # ====================================================

        "estimated_monthly_saving": _pick(
            run_data,
            "estimated_monthly_saving",
        ),

        "saving_rate": _pick(
            run_data,
            "saving_rate",
        ),

        "total_elapsed_time": _pick(
            run_data,
            "total_elapsed_time",
            "elapsed_time",
        ),

        # ====================================================
        # HITL
        # ====================================================

        "approval_required": bool(
            _pick(
                run_data,
                "approval_required",
                default=False,
            )
        ),

        "max_risk_level": _pick(
            run_data,
            "max_risk_level",
        ),

        "approval_decision": _pick(
            run_data,
            "approval_decision",
        ),

        "approval_operator": _pick(
            run_data,
            "approval_operator",
        ),

        "approved_scope": _pick(
            run_data,
            "approved_scope",
        ),

        # ====================================================
        # 工作流明细
        # ====================================================

        "workflow_steps": [
            _build_workflow_step(row)
            for row in workflow_rows
        ],

        # ====================================================
        # 优化项
        # ====================================================

        "optimization_items": [
            _build_optimization_item(row)
            for row in optimization_rows
        ],

        # ====================================================
        # 审批记录
        # ====================================================

        "approvals": [
            _build_approval(row)
            for row in approval_rows
        ],

        # ====================================================
        # 报告
        # ====================================================

        "reports": [
            _build_report(row)
            for row in report_rows
        ],

        "created_at": _pick(
            run_data,
            "created_at",
        ),

        "updated_at": _pick(
            run_data,
            "updated_at",
        ),
    }


# ============================================================
# 3. 待人工审批列表
# ============================================================

def list_pending_runs(
    db: Session,
) -> dict[str, Any]:

    query = db.query(AgentRun)

    # 当前 CloudCostOps 工作流暂停时，
    # status = pending_approval
    if hasattr(AgentRun, "status"):
        query = query.filter(
            AgentRun.status == "pending_approval"
        )

    if hasattr(AgentRun, "created_at"):
        query = query.order_by(
            AgentRun.created_at.desc()
        )

    rows = query.all()

    items: list[dict[str, Any]] = []

    for run in rows:

        run_data = _model_to_dict(run)

        run_id = _pick(
            run_data,
            "run_id",
            default="",
        )

        optimization_rows = _query_by_run_id(
            db,
            OptimizationItem,
            run_id,
        )

        optimization_items = [
            _build_optimization_item(row)
            for row in optimization_rows
        ]

        # 只统计需要人工审批的资源
        approval_items = [
            item
            for item in optimization_items
            if item.get("need_human_approval")
        ]

        items.append(
            {
                "run_id": run_id,

                "status": _pick(
                    run_data,
                    "status",
                ),

                "max_risk_level": _pick(
                    run_data,
                    "max_risk_level",
                ),

                "approval_count": len(
                    approval_items
                ),

                "estimated_monthly_saving": _pick(
                    run_data,
                    "estimated_monthly_saving",
                ),

                "optimization_items": approval_items,

                "created_at": _pick(
                    run_data,
                    "created_at",
                ),
            }
        )

    return {
        "success": True,
        "total": len(items),
        "items": items,
    }