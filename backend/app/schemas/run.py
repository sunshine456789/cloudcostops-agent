from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================
# 通用子结构
# ============================================================

class WorkflowStepResponse(BaseModel):
    """Agent 工作流单个执行步骤"""

    step_id: Optional[int] = None

    agent_name: Optional[str] = None
    stage: Optional[str] = None

    status: Optional[str] = None
    status_label: Optional[str] = None

    duration_ms: Optional[int] = 0

    action: Optional[str] = None
    key_output: Optional[str] = None

    evidence: Any = None


class OptimizationItemResponse(BaseModel):
    """云资源优化建议"""

    resource_id: Optional[str] = None
    service: Optional[str] = None
    env: Optional[str] = None
    owner: Optional[str] = None
    region: Optional[str] = None

    avg_cpu_utilization: Optional[float] = None
    avg_memory_utilization: Optional[float] = None
    avg_disk_utilization: Optional[float] = None
    avg_gpu_utilization: Optional[float] = None

    monthly_cost: Optional[float] = None

    issue_type: Optional[str] = None
    recommend_action: Optional[str] = None

    estimated_monthly_saving: Optional[float] = None

    risk_level: Optional[str] = None
    need_human_approval: Optional[bool] = False

    reason: Optional[str] = None


class ApprovalDecisionResponse(BaseModel):
    """人工审批记录"""

    decision: Optional[str] = None
    operator: Optional[str] = None
    comment: Optional[str] = None
    approved_scope: Optional[str] = None

    created_at: Optional[str] = None


class GeneratedReportResponse(BaseModel):
    """自动生成的成本优化报告"""

    report_id: Optional[str] = None
    report_filename: Optional[str] = None
    report_path: Optional[str] = None
    report_saved: Optional[bool] = None

    created_at: Optional[str] = None


# ============================================================
# Agent Run 列表
# ============================================================

class AgentRunListItem(BaseModel):
    """任务列表中的一条记录"""

    run_id: str

    status: Optional[str] = None
    workflow_engine: Optional[str] = None

    approval_required: Optional[bool] = False
    max_risk_level: Optional[str] = None

    approval_decision: Optional[str] = None
    approval_operator: Optional[str] = None
    approved_scope: Optional[str] = None

    estimated_monthly_saving: Optional[float] = None
    saving_rate: Optional[float] = None

    billing_filename: Optional[str] = None
    utilization_filename: Optional[str] = None

    total_elapsed_time: Optional[float] = None

    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AgentRunListResponse(BaseModel):
    """历史任务列表响应"""

    success: bool = True

    total: int = 0
    page: int = 1
    page_size: int = 20

    items: list[AgentRunListItem] = Field(default_factory=list)


# ============================================================
# Agent Run 详情
# ============================================================

class AgentRunDetailResponse(BaseModel):
    """单个 Agent Workflow 完整详情"""

    success: bool = True

    run_id: str

    status: Optional[str] = None
    workflow_engine: Optional[str] = None

    # ---------- LLM ----------
    llm_enabled: Optional[bool] = None
    llm_model: Optional[str] = None
    llm_error: Optional[str] = None

    # ---------- 文件 ----------
    billing_filename: Optional[str] = None
    utilization_filename: Optional[str] = None

    # ---------- 成本 ----------
    estimated_monthly_saving: Optional[float] = None
    saving_rate: Optional[float] = None
    total_elapsed_time: Optional[float] = None

    # ---------- HITL ----------
    approval_required: Optional[bool] = False
    max_risk_level: Optional[str] = None

    approval_decision: Optional[str] = None
    approval_operator: Optional[str] = None
    approved_scope: Optional[str] = None

    # ---------- 工作流 ----------
    workflow_steps: list[WorkflowStepResponse] = Field(
        default_factory=list
    )

    # ---------- 优化资源 ----------
    optimization_items: list[OptimizationItemResponse] = Field(
        default_factory=list
    )

    # ---------- 审批历史 ----------
    approvals: list[ApprovalDecisionResponse] = Field(
        default_factory=list
    )

    # ---------- 报告 ----------
    reports: list[GeneratedReportResponse] = Field(
        default_factory=list
    )

    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ============================================================
# Pending Approval
# ============================================================

class PendingApprovalItem(BaseModel):
    """待人工审批任务"""

    run_id: str

    status: Optional[str] = None

    max_risk_level: Optional[str] = None

    approval_count: int = 0

    estimated_monthly_saving: Optional[float] = None

    optimization_items: list[OptimizationItemResponse] = Field(
        default_factory=list
    )

    created_at: Optional[str] = None


class PendingApprovalListResponse(BaseModel):
    """待审批任务列表"""

    success: bool = True

    total: int = 0

    items: list[PendingApprovalItem] = Field(
        default_factory=list
    )