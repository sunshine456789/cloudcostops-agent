from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.schemas.approval import ApprovalDecision
from backend.app.services.upload_service import (
    remove_files,
    save_csv_upload,
)
from backend.audit_logger import log_approval_decision
from backend.cost_analyzer import analyze_billing
from backend.optimization_agent import generate_optimization_plan
from backend.utilization_analyzer import analyze_utilization


router = APIRouter(prefix="/agent")


@router.post("/optimization-plan")
async def generate_plan(
    billing_file: UploadFile = File(...),
    utilization_file: UploadFile = File(...),
) -> dict[str, Any]:
    start_time = time.perf_counter()

    billing_path: Path | None = None
    utilization_path: Path | None = None

    billing_name = billing_file.filename or "billing.csv"
    utilization_name = (
        utilization_file.filename or "utilization.csv"
    )

    try:
        billing_path = save_csv_upload(
            upload=billing_file,
            prefix="billing",
        )
        utilization_path = save_csv_upload(
            upload=utilization_file,
            prefix="utilization",
        )

        billing_result = analyze_billing(
            str(billing_path)
        )
        utilization_result = analyze_utilization(
            str(utilization_path)
        )

        agent_result = generate_optimization_plan(
            billing_result=billing_result,
            utilization_result=utilization_result,
        )

        return {
            **agent_result,
            "billing_filename": billing_name,
            "utilization_filename": utilization_name,
            "total_elapsed_time": round(
                time.perf_counter() - start_time,
                3,
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
            detail=f"生成成本优化方案失败：{exc}",
        ) from exc

    finally:
        remove_files(
            billing_path,
            utilization_path,
        )


@router.post("/approval-decision")
async def submit_approval_decision(
    decision: ApprovalDecision,
) -> dict[str, Any]:
    try:
        return log_approval_decision(
            decision.model_dump()
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"审批决策记录失败：{exc}",
        ) from exc