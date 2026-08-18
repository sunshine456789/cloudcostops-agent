from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.agents.cloud_cost.graph import (
    resume_cloud_cost_graph,
    run_cloud_cost_graph,
)
from backend.app.schemas.approval import ApprovalDecision
from backend.app.services.run_persistence_service import persist_agent_result
from backend.app.services.upload_service import remove_files, save_csv_upload
from backend.audit_logger import log_approval_decision


router = APIRouter(prefix="/agent")


def _persist_result_safely(result: dict[str, Any]) -> dict[str, Any]:
    """
    安全持久化 Agent 运行结果。

    数据库持久化失败时，
    不影响已经完成的 LangGraph 主流程结果返回。
    """
    try:
        return persist_agent_result(result)

    except Exception as exc:
        return {
            "success": False,
            "run_id": result.get("run_id"),
            "error": str(exc),
        }


@router.post(
    "/optimization-plan",
    summary="Generate Plan",
)
async def generate_plan(
    billing_file: UploadFile = File(...),
    utilization_file: UploadFile = File(...),
) -> dict[str, Any]:
    """
    上传云账单与资源利用率 CSV，
    启动 CloudCostOps LangGraph 工作流并持久化结果。
    """

    start_time = time.perf_counter()

    billing_path: Path | None = None
    utilization_path: Path | None = None

    billing_name = (
        billing_file.filename
        or "billing.csv"
    )

    utilization_name = (
        utilization_file.filename
        or "utilization.csv"
    )

    try:
        # ====================================================
        # 1. 保存上传文件
        # ====================================================

        billing_path = save_csv_upload(
            upload=billing_file,
            prefix="billing",
        )

        utilization_path = save_csv_upload(
            upload=utilization_file,
            prefix="utilization",
        )

        # ====================================================
        # 2. 执行 LangGraph Multi-Agent 工作流
        # ====================================================

        agent_result = run_cloud_cost_graph(
            billing_path=str(billing_path),
            utilization_path=str(utilization_path),
        )

        # ====================================================
        # 3. 补充 API 层元数据
        # ====================================================
        #
        # 非常重要：
        #
        # billing_filename
        # utilization_filename
        # total_elapsed_time
        #
        # 这些数据只有 API 层最容易获得。
        #
        # 原来的逻辑是在数据库持久化完成以后，
        # 才把这些字段加入 Response。
        #
        # 这样会导致：
        #
        # GET /runs
        #
        # 中这些字段一直为 null。
        #
        # 所以现在必须：
        #
        # 先构造 enriched_result
        # 再进行数据库持久化。
        # ====================================================

        enriched_result: dict[str, Any] = {
            **agent_result,

            "billing_filename": (
                billing_name
            ),

            "utilization_filename": (
                utilization_name
            ),

            "total_elapsed_time": round(
                time.perf_counter()
                - start_time,
                3,
            ),
        }

        # ====================================================
        # 4. 数据库持久化
        # ====================================================

        persistence_result = (
            _persist_result_safely(
                enriched_result
            )
        )

        # ====================================================
        # 5. API Response
        # ====================================================

        return {
            **enriched_result,

            "persistence": (
                persistence_result
            ),
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "生成成本优化方案失败："
                f"{exc}"
            ),
        ) from exc

    finally:
        # ====================================================
        # 6. 删除临时上传文件
        # ====================================================

        remove_files(
            billing_path,
            utilization_path,
        )


@router.post(
    "/approval-decision",
    summary="Submit Approval Decision",
)
async def submit_approval_decision(
    decision: ApprovalDecision,
) -> dict[str, Any]:
    """
    提交人工审批结果，
    并恢复暂停状态下的 LangGraph HITL 工作流。

    支持：

        approve
        reject

    审批信息会同时：

        1. 恢复 LangGraph
        2. 更新 agent_runs
        3. 写入 approval_decisions
        4. 保存 workflow_steps
        5. 保存 optimization_items
        6. 保存 generated_reports
    """

    approval_payload = (
        decision.model_dump()
    )

    try:
        # ====================================================
        # 1. Resume LangGraph
        # ====================================================

        result = resume_cloud_cost_graph(
            run_id=decision.run_id,
            approval_payload=(
                approval_payload
            ),
        )

        # ====================================================
        # 2. 强制补充人工审批信息
        # ====================================================
        #
        # 这些信息最可靠的来源是 API Request。
        #
        # 不能完全依赖 Graph 最终状态是否再次返回。
        #
        # 否则容易出现：
        #
        # approval_decision = null
        # approval_operator = null
        # approved_scope = null
        #
        # ====================================================

        enriched_result: dict[str, Any] = {
            **result,

            "run_id": (
                decision.run_id
            ),

            "approval_decision": (
                approval_payload.get(
                    "decision"
                )
            ),

            "approval_operator": (
                approval_payload.get(
                    "operator"
                )
            ),

            "approval_comment": (
                approval_payload.get(
                    "comment"
                )
            ),

            "approved_scope": (
                approval_payload.get(
                    "approved_scope"
                )
            ),
        }

        # ====================================================
        # 3. 将恢复后的状态重新写入数据库
        # ====================================================
        #
        # pending_approval
        #
        #       ↓
        #
        # completed
        #
        # 或：
        #
        # rejected
        #
        # ====================================================

        persistence_result = (
            _persist_result_safely(
                enriched_result
            )
        )

        # ====================================================
        # 4. 保留原有 Audit Log
        # ====================================================

        log_approval_decision({
            **approval_payload,

            "workflow_status": (
                enriched_result.get(
                    "status"
                )
            ),
        })

        # ====================================================
        # 5. Response
        # ====================================================

        return {
            **enriched_result,

            "persistence": (
                persistence_result
            ),
        }

    except ValueError as exc:
        # 常见情况：
        #
        # 1. run_id 不存在
        # 2. 工作流已经 completed
        # 3. 工作流已经 rejected
        # 4. 当前任务不存在 interrupt
        #
        # 使用 409 Conflict 比较合适。

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "审批并恢复工作流失败："
                f"{exc}"
            ),
        ) from exc