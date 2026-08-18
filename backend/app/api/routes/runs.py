from __future__ import annotations

from typing import Generator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.services.run_query_service import (
    get_agent_run_detail,
    list_agent_runs,
    list_pending_runs,
)


router = APIRouter()


# ============================================================
# Database Dependency
# ============================================================

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 数据库 Session 依赖。

    每次 HTTP 请求创建一个数据库 Session，
    请求结束后自动关闭。
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# 1. Agent Run 历史列表
# ============================================================

@router.get(
    "",
    summary="List Agent Runs",
    description="分页查询 CloudCostOps Agent 历史工作流运行记录。",
)
def get_runs(
    page: int = Query(
        default=1,
        ge=1,
        description="页码，从 1 开始",
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="每页记录数量",
    ),
    status: Optional[str] = Query(
        default=None,
        description=(
            "工作流状态过滤，例如："
            "pending_approval / completed / rejected / failed"
        ),
    ),
    approval_required: Optional[bool] = Query(
        default=None,
        description="是否只查询需要人工审批的任务",
    ),
    db: Session = Depends(get_db),
):
    """
    查询 Agent Run 历史记录。

    可用于 React 管理后台：

    - 任务中心
    - 历史运行记录
    - 状态筛选
    - HITL 审批任务筛选
    """

    return list_agent_runs(
        db=db,
        page=page,
        page_size=page_size,
        status=status,
        approval_required=approval_required,
    )


# ============================================================
# 2. 待人工审批任务
# ============================================================

@router.get(
    "/pending",
    summary="List Pending Approval Runs",
    description="查询所有等待人工审批的 CloudCostOps Agent 工作流。",
)
def get_pending_runs(
    db: Session = Depends(get_db),
):
    """
    获取当前所有 pending_approval 工作流。

    后续 React Approval Center
    会直接使用这个接口。
    """

    return list_pending_runs(db)


# ============================================================
# 3. 单次 Run 完整详情
# ============================================================

@router.get(
    "/{run_id}",
    summary="Get Agent Run Detail",
    description=(
        "查询单次 CloudCostOps Agent 工作流的完整执行详情，"
        "包含 Workflow Steps、优化建议、审批记录和生成报告。"
    ),
)
def get_run_detail(
    run_id: str,
    db: Session = Depends(get_db),
):
    """
    根据 run_id 查询完整运行详情。
    """

    result = get_agent_run_detail(
        db=db,
        run_id=run_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent Run 不存在: {run_id}",
        )

    return result