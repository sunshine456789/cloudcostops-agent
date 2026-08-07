from __future__ import annotations

from typing import Any, TypedDict


class CloudCostState(TypedDict, total=False):
    """CloudCostOps LangGraph 共享状态。"""

    run_id: str

    billing_path: str
    utilization_path: str

    billing_result: dict[str, Any]
    utilization_result: dict[str, Any]
    plan_result: dict[str, Any]

    approval_items: list[dict[str, Any]]
    approval_required: bool
    max_risk_level: str

    workflow_steps: list[dict[str, Any]]

    status: str
    error: str