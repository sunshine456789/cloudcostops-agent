from typing import Literal

from pydantic import BaseModel, Field


ApprovalScope = Literal[
    "low_risk_only",
    "manual_review_required",
    "reject_all",
    "record_only",
]


class ApprovalDecision(BaseModel):
    run_id: str = Field(
        ...,
        min_length=1,
        description="Agent 优化任务的运行 ID",
    )
    decision: str = Field(
        ...,
        min_length=1,
        description="审批人做出的决策",
    )
    operator: str = Field(
        default="demo_user",
        min_length=1,
        description="审批操作人",
    )
    comment: str = Field(
        default="",
        description="审批备注",
    )
    approved_scope: ApprovalScope = Field(
        default="low_risk_only",
        description="允许执行的优化范围",
    )