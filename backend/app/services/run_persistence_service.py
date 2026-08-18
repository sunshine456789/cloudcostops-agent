from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.sql.sqltypes import JSON

from backend.app.db.models import (
    AgentRun,
    ApprovalDecision,
    GeneratedReport,
    OptimizationItem,
    WorkflowStep,
)
from backend.app.db.session import SessionLocal
from backend.app.repositories.cloudcost_repository import (
    add_approval_decision,
    replace_optimization_items,
    replace_workflow_steps,
    save_agent_run,
    save_generated_report,
)


# ============================================================
# ORM Compatibility Helpers
# ============================================================

def _mapped_columns(model) -> dict[str, tuple[str, Any]]:
    """
    同时支持：

    1. SQLAlchemy ORM 属性名
    2. 数据库真实列名

    防止 ORM 属性名与数据库 column.name 不完全一致时，
    持久化字段被静默忽略。
    """

    mapper = sa_inspect(model)

    result: dict[str, tuple[str, Any]] = {}

    for attr in mapper.column_attrs:
        column = attr.columns[0]

        # ORM attribute key
        result[attr.key] = (
            attr.key,
            column,
        )

        # real database column name
        result[column.name] = (
            attr.key,
            column,
        )

    return result


def _normalize_value(
    column,
    value,
):
    """
    dict/list：

        JSON 字段
            -> 原样保存

        String/Text 字段
            -> JSON 字符串
    """

    if value is None:
        return None

    if isinstance(
        value,
        (dict, list),
    ):
        if isinstance(
            column.type,
            JSON,
        ):
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

    aliases 用于兼容不同版本字段命名。
    """

    aliases = aliases or {}

    mapped = _mapped_columns(
        model
    )

    payload: dict[str, Any] = {}

    for source_name, value in values.items():

        candidate_names = [
            source_name,
            *aliases.get(
                source_name,
                [],
            ),
        ]

        for candidate in candidate_names:

            target = mapped.get(
                candidate
            )

            if target is None:
                continue

            attr_name, column = target

            payload[attr_name] = (
                _normalize_value(
                    column,
                    value,
                )
            )

            break

    return model(
        **payload
    )


# ============================================================
# Generic Helpers
# ============================================================

def _first_not_none(
    *values,
):
    for value in values:
        if value is not None:
            return value

    return None


def _as_dict(
    value: Any,
) -> dict[str, Any]:

    if isinstance(
        value,
        dict,
    ):
        return value

    return {}


def _iter_strings(
    value: Any,
):
    """
    递归提取 dict/list/evidence 中的字符串。
    """

    if isinstance(
        value,
        str,
    ):
        yield value

    elif isinstance(
        value,
        dict,
    ):
        for item in value.values():
            yield from _iter_strings(
                item
            )

    elif isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        for item in value:
            yield from _iter_strings(
                item
            )


def _extract_step_kv(
    result: dict[str, Any],
    key: str,
) -> str | None:
    """
    从 workflow_steps.evidence 中兜底提取：

        llm_enabled=True
        llm_model=deepseek-v4-pro
        billing_file=xxx.csv
        utilization_file=xxx.csv
    """

    pattern = re.compile(
        rf"(?:^|\b){re.escape(key)}\s*=\s*([^,;\s]+)",
        re.IGNORECASE,
    )

    for step in (
        result.get(
            "workflow_steps"
        )
        or []
    ):

        if not isinstance(
            step,
            dict,
        ):
            continue

        for text in _iter_strings(
            step.get(
                "evidence"
            )
        ):

            match = pattern.search(
                text
            )

            if match:
                return (
                    match.group(1)
                    .strip()
                    .strip("\"'")
                )

    return None


# ============================================================
# Input File Helpers
# ============================================================

def _clean_uploaded_filename(
    value: Any,
    kind: str,
) -> str | None:
    """
    临时上传文件可能为：

        billing_abcd1234_cloud_billing_sample.csv

    最终希望保存：

        cloud_billing_sample.csv
    """

    if value in (
        None,
        "",
    ):
        return None

    try:
        name = Path(
            str(value)
        ).name

    except Exception:
        name = str(
            value
        )

    pattern = re.compile(
        rf"^{re.escape(kind)}_[0-9a-fA-F]{{8,}}_(.+)$"
    )

    match = pattern.match(
        name
    )

    if match:
        return match.group(
            1
        )

    return name


def _extract_input_filename(
    result: dict[str, Any],
    kind: str,
) -> str | None:

    if kind == "billing":

        direct = _first_not_none(
            result.get(
                "billing_filename"
            ),
            result.get(
                "billing_file_name"
            ),
            result.get(
                "billing_file"
            ),
            result.get(
                "billing_path"
            ),
        )

        evidence_key = (
            "billing_file"
        )

    else:

        direct = _first_not_none(
            result.get(
                "utilization_filename"
            ),
            result.get(
                "utilization_file_name"
            ),
            result.get(
                "utilization_file"
            ),
            result.get(
                "utilization_path"
            ),
        )

        evidence_key = (
            "utilization_file"
        )

    # --------------------------------------------------------
    # 如果 endpoint 在 persistence 之后才添加 filename，
    # 尝试从 workflow step evidence 兜底恢复
    # --------------------------------------------------------

    if direct is None:
        direct = (
            _extract_step_kv(
                result,
                evidence_key,
            )
        )

    return (
        _clean_uploaded_filename(
            direct,
            kind,
        )
    )


# ============================================================
# Performance Helper
# ============================================================

def _extract_total_elapsed_time(
    result: dict[str, Any],
) -> float | int | None:

    value = _first_not_none(
        result.get(
            "total_elapsed_time"
        ),
        result.get(
            "elapsed_time"
        ),
        result.get(
            "elapsed_time_s"
        ),
        result.get(
            "elapsed_seconds"
        ),
    )

    if value is not None:
        return value

    # --------------------------------------------------------
    # fallback:
    #
    # workflow_summary.total_duration_ms
    #       ->
    # seconds
    # --------------------------------------------------------

    summary = _as_dict(
        result.get(
            "workflow_summary"
        )
    )

    duration_ms = summary.get(
        "total_duration_ms"
    )

    if duration_ms is not None:

        try:
            return round(
                float(
                    duration_ms
                )
                / 1000.0,
                3,
            )

        except (
            TypeError,
            ValueError,
        ):
            pass

    return None


# ============================================================
# LLM Helper
# ============================================================

def _extract_bool(
    value: Any,
) -> bool | None:

    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        return value

    text = (
        str(
            value
        )
        .strip()
        .lower()
    )

    if text in {
        "true",
        "1",
        "yes",
        "y",
        "on",
    }:
        return True

    if text in {
        "false",
        "0",
        "no",
        "n",
        "off",
    }:
        return False

    return None


# ============================================================
# Approval Helper
# ============================================================

def _extract_approval(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    同时兼容：

        result["approval_decision"]

    以及：

        result["approval"]["decision"]
        result["approval_result"]["decision"]
        result["human_approval"]["decision"]
    """

    nested = _as_dict(
        _first_not_none(
            result.get(
                "approval"
            ),
            result.get(
                "approval_result"
            ),
            result.get(
                "human_approval"
            ),
        )
    )

    decision = _first_not_none(
        result.get(
            "approval_decision"
        ),
        nested.get(
            "approval_decision"
        ),
        nested.get(
            "decision"
        ),
    )

    operator = _first_not_none(
        result.get(
            "approval_operator"
        ),
        nested.get(
            "approval_operator"
        ),
        nested.get(
            "operator"
        ),
    )

    comment = _first_not_none(
        result.get(
            "approval_comment"
        ),
        nested.get(
            "approval_comment"
        ),
        nested.get(
            "comment"
        ),
    )

    approved_scope = _first_not_none(
        result.get(
            "approved_scope"
        ),
        nested.get(
            "approved_scope"
        ),
        nested.get(
            "scope"
        ),
    )

    return {
        "decision": decision,
        "operator": operator,
        "comment": comment,
        "approved_scope": approved_scope,
    }


# ============================================================
# AgentRun
# ============================================================

def _build_agent_run(
    result: dict[str, Any],
) -> AgentRun:

    approval = (
        _extract_approval(
            result
        )
    )

    # --------------------------------------------------------
    # LLM
    # --------------------------------------------------------

    llm_enabled = _extract_bool(
        _first_not_none(
            result.get(
                "llm_enabled"
            ),
            _extract_step_kv(
                result,
                "llm_enabled",
            ),
        )
    )

    llm_model = _first_not_none(
        result.get(
            "llm_model"
        ),
        _extract_step_kv(
            result,
            "llm_model",
        ),
    )

    values = {

        # Core
        "run_id": (
            result.get(
                "run_id"
            )
        ),

        "status": (
            result.get(
                "status"
            )
        ),

        "workflow_engine": (
            result.get(
                "workflow_engine"
            )
        ),

        # LLM
        "llm_enabled": (
            llm_enabled
        ),

        "llm_model": (
            llm_model
        ),

        "llm_error": (
            result.get(
                "llm_error"
            )
        ),

        # Risk
        "max_risk_level": (
            result.get(
                "max_risk_level"
            )
        ),

        # Approval
        "approval_required": (
            result.get(
                "approval_required"
            )
        ),

        "approval_decision": (
            approval[
                "decision"
            ]
        ),

        "approval_operator": (
            approval[
                "operator"
            ]
        ),

        "approval_comment": (
            approval[
                "comment"
            ]
        ),

        "approved_scope": (
            approval[
                "approved_scope"
            ]
        ),

        # Cost
        "estimated_monthly_saving": (
            result.get(
                "estimated_monthly_saving"
            )
        ),

        "saving_rate": (
            result.get(
                "saving_rate"
            )
        ),

        # Input Files
        "billing_filename": (
            _extract_input_filename(
                result,
                "billing",
            )
        ),

        "utilization_filename": (
            _extract_input_filename(
                result,
                "utilization",
            )
        ),

        # Performance
        "total_elapsed_time": (
            _extract_total_elapsed_time(
                result
            )
        ),
    }

    status = result.get(
        "status"
    )

    if status in {
        "completed",
        "rejected",
        "failed",
    }:

        values[
            "completed_at"
        ] = datetime.utcnow()

    return _create_model(
        AgentRun,
        values,
        aliases={

            "llm_enabled": [
                "use_llm",
                "is_llm_enabled",
            ],

            "llm_model": [
                "model_name",
            ],

            "llm_error": [
                "model_error",
            ],

            "approval_decision": [
                "decision",
            ],

            "approval_operator": [
                "operator",
            ],

            "approval_comment": [
                "comment",
            ],

            "approved_scope": [
                "scope",
            ],

            "billing_filename": [
                "billing_file_name",
                "billing_file",
            ],

            "utilization_filename": [
                "utilization_file_name",
                "utilization_file",
            ],

            "total_elapsed_time": [
                "elapsed_time",
                "elapsed_time_s",
            ],
        },
    )


# ============================================================
# WorkflowStep
# ============================================================

def _build_workflow_steps(
    result: dict[str, Any],
) -> tuple[
    list[WorkflowStep],
    bool,
]:
    """
    第二个返回值表示：

        当前 result 中是否真的携带 workflow_steps

    这样 Resume 返回部分数据时，
    不会把数据库中已有步骤误删。
    """

    if "workflow_steps" not in result:
        return (
            [],
            False,
        )

    run_id = result.get(
        "run_id"
    )

    raw_steps = (
        result.get(
            "workflow_steps"
        )
        or []
    )

    objects: list[
        WorkflowStep
    ] = []

    for index, step in enumerate(
        raw_steps,
        start=1,
    ):

        if not isinstance(
            step,
            dict,
        ):
            continue

        values = {

            "run_id": run_id,

            "step_id": (
                step.get(
                    "step_id",
                    index,
                )
            ),

            "agent_name": (
                step.get(
                    "agent_name"
                )
            ),

            "stage": (
                step.get(
                    "stage"
                )
            ),

            "status": (
                step.get(
                    "status"
                )
            ),

            "status_label": (
                step.get(
                    "status_label"
                )
            ),

            "duration_ms": (
                step.get(
                    "duration_ms"
                )
            ),

            "action": (
                step.get(
                    "action"
                )
            ),

            "key_output": (
                step.get(
                    "key_output"
                )
            ),

            "evidence": (
                step.get(
                    "evidence"
                )
            ),
        }

        objects.append(
            _create_model(
                WorkflowStep,
                values,
                aliases={

                    "evidence": [
                        "evidence_json",
                        "evidence_text",
                    ],
                },
            )
        )

    return (
        objects,
        True,
    )


# ============================================================
# OptimizationItem
# ============================================================

def _get_raw_optimization_items(
    result: dict[str, Any],
) -> tuple[
    list[Any],
    bool,
]:

    for key in (
        "optimization_items",
        "recommendations",
        "approval_items",
    ):

        if key in result:

            value = result.get(
                key
            )

            if isinstance(
                value,
                list,
            ):
                return (
                    value,
                    True,
                )

            return (
                [],
                True,
            )

    return (
        [],
        False,
    )


def _build_optimization_items(
    result: dict[str, Any],
) -> tuple[
    list[OptimizationItem],
    bool,
]:

    run_id = result.get(
        "run_id"
    )

    raw_items, present = (
        _get_raw_optimization_items(
            result
        )
    )

    if not present:
        return (
            [],
            False,
        )

    objects: list[
        OptimizationItem
    ] = []

    for item in raw_items:

        if not isinstance(
            item,
            dict,
        ):
            continue

        values = {

            "run_id": run_id,

            "resource_id": (
                item.get(
                    "resource_id"
                )
            ),

            "service": (
                item.get(
                    "service"
                )
            ),

            "env": (
                item.get(
                    "env"
                )
            ),

            "owner": (
                item.get(
                    "owner"
                )
            ),

            "region": (
                item.get(
                    "region"
                )
            ),

            "avg_cpu_utilization": (
                item.get(
                    "avg_cpu_utilization"
                )
            ),

            "avg_memory_utilization": (
                item.get(
                    "avg_memory_utilization"
                )
            ),

            "avg_disk_utilization": (
                item.get(
                    "avg_disk_utilization"
                )
            ),

            "avg_gpu_utilization": (
                item.get(
                    "avg_gpu_utilization"
                )
            ),

            "monthly_cost": (
                item.get(
                    "monthly_cost"
                )
            ),

            "issue_type": (
                item.get(
                    "issue_type"
                )
            ),

            "recommend_action": (
                _first_not_none(
                    item.get(
                        "recommend_action"
                    ),
                    item.get(
                        "recommended_action"
                    ),
                    item.get(
                        "action"
                    ),
                )
            ),

            "estimated_monthly_saving": (
                item.get(
                    "estimated_monthly_saving"
                )
            ),

            "risk_level": (
                item.get(
                    "risk_level"
                )
            ),

            "need_human_approval": (
                item.get(
                    "need_human_approval"
                )
            ),

            "reason": (
                item.get(
                    "reason"
                )
            ),
        }

        objects.append(
            _create_model(
                OptimizationItem,
                values,
                aliases={

                    "recommend_action": [
                        "recommended_action",
                        "action",
                    ],
                },
            )
        )

    return (
        objects,
        True,
    )


# ============================================================
# GeneratedReport
# ============================================================

def _build_report(
    result: dict[str, Any],
) -> GeneratedReport | None:

    report_id = result.get(
        "report_id"
    )

    if not report_id:
        return None

    values = {

        "report_id": report_id,

        "run_id": (
            result.get(
                "run_id"
            )
        ),

        "report_filename": (
            result.get(
                "report_filename"
            )
        ),

        "report_path": (
            result.get(
                "report_path"
            )
        ),

        "report_type": (
            result.get(
                "report_type"
            )
            or
            "cost_optimization"
        ),

        "report_saved": (
            result.get(
                "report_saved"
            )
        ),
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

            "report_saved": [
                "saved",
            ],
        },
    )


# ============================================================
# ApprovalDecision
# ============================================================

def _build_approval_decision(
    result: dict[str, Any],
) -> ApprovalDecision | None:

    approval = (
        _extract_approval(
            result
        )
    )

    if not approval[
        "decision"
    ]:
        return None

    values = {

        "run_id": (
            result.get(
                "run_id"
            )
        ),

        "decision": (
            approval[
                "decision"
            ]
        ),

        "operator": (
            approval[
                "operator"
            ]
        ),

        "comment": (
            approval[
                "comment"
            ]
        ),

        "approved_scope": (
            approval[
                "approved_scope"
            ]
        ),
    }

    return _create_model(
        ApprovalDecision,
        values,
        aliases={

            "decision": [
                "approval_decision",
            ],

            "operator": [
                "approval_operator",
            ],

            "comment": [
                "approval_comment",
            ],
        },
    )


# ============================================================
# Main Persistence
# ============================================================

def persist_agent_result(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    将一次 CloudCostOps Agent 运行结果完整写入数据库。

    特点：

    1. AgentRun 使用 Upsert
    2. 不用 None 覆盖旧值
    3. workflow_steps 只有真正返回时才替换
    4. optimization_items 只有真正返回时才替换
    5. ApprovalDecision 保存审批历史
    6. GeneratedReport 保存报告
    7. 所有操作处于一个数据库事务
    """

    run_id = result.get(
        "run_id"
    )

    if not run_id:

        raise ValueError(
            "LangGraph result 缺少 run_id，"
            "无法进行数据库持久化。"
        )

    db = SessionLocal()

    try:

        # ====================================================
        # 1. AgentRun
        # ====================================================

        run = (
            _build_agent_run(
                result
            )
        )

        saved_run = (
            save_agent_run(
                db,
                run,
            )
        )

        # ====================================================
        # 2. Workflow Steps
        # ====================================================

        (
            workflow_steps,
            workflow_steps_present,
        ) = _build_workflow_steps(
            result
        )

        if workflow_steps_present:

            replace_workflow_steps(
                db,
                run_id,
                workflow_steps,
            )

        # ====================================================
        # 3. Optimization Items
        # ====================================================

        (
            optimization_items,
            optimization_items_present,
        ) = _build_optimization_items(
            result
        )

        if optimization_items_present:

            replace_optimization_items(
                db,
                run_id,
                optimization_items,
            )

        # ====================================================
        # 4. Generated Report
        # ====================================================

        report = (
            _build_report(
                result
            )
        )

        if report is not None:

            save_generated_report(
                db,
                report,
            )

        # ====================================================
        # 5. Approval History
        # ====================================================

        approval = (
            _build_approval_decision(
                result
            )
        )

        if approval is not None:

            add_approval_decision(
                db,
                approval,
            )

        # ====================================================
        # 6. Commit
        # ====================================================

        db.commit()

        db.refresh(
            saved_run
        )

        return {

            "success": True,

            "run_id": run_id,

            "workflow_step_count": (
                len(
                    workflow_steps
                )
                if workflow_steps_present
                else None
            ),

            "optimization_item_count": (
                len(
                    optimization_items
                )
                if optimization_items_present
                else None
            ),

            "report_saved": (
                report
                is not None
            ),

            "approval_saved": (
                approval
                is not None
            ),

            "agent_run_status": (
                getattr(
                    saved_run,
                    "status",
                    None,
                )
            ),
        }

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()