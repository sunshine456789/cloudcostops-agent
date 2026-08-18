from __future__ import annotations

from typing import Any, TypedDict


class CloudCostState(TypedDict, total=False):
    """CloudCostOps LangGraph 共享状态。"""

    # 任务标识
    run_id: str

    # 输入数据
    billing_path: str
    utilization_path: str

    # 分析结果
    billing_result: dict[str, Any]
    utilization_result: dict[str, Any]
    plan_result: dict[str, Any]

    # 风险与审批
    approval_items: list[dict[str, Any]]
    approval_required: bool
    max_risk_level: str

    approval_decision: str
    approval_operator: str
    approval_comment: str
    approved_scope: str

    # 用于统计真正等待人工审批的时间
    approval_requested_at: float

    # 工作流轨迹
    workflow_steps: list[dict[str, Any]]

    # 整体状态
    status: str
    error: str