from typing import Literal

from pydantic import BaseModel, Field


ApprovalDecisionType = Literal[
    "approve",
    "reject",
]


ApprovalScope = Literal[
    "all_proposed",
    "low_risk_only",
    "none",
]


class ApprovalDecision(BaseModel):
    run_id: str = Field(
        ...,
        min_length=1,
        description=(
            "需要恢复的 LangGraph run_id"
        ),
    )

    decision: ApprovalDecisionType = Field(
        ...,
        description=(
            "approve 表示批准，"
            "reject 表示拒绝"
        ),
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
        default="all_proposed",
        description="批准范围",
    )