from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.services.upload_service import (
    remove_files,
    save_csv_upload,
)
from backend.cost_analyzer import analyze_billing
from backend.utilization_analyzer import analyze_utilization


router = APIRouter(prefix="/analyze")


@router.post("/billing")
async def analyze_billing_file(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    start_time = time.perf_counter()
    saved_path: Path | None = None
    original_name = file.filename or "unknown.csv"

    try:
        saved_path = save_csv_upload(
            upload=file,
            prefix="billing",
        )

        result = analyze_billing(str(saved_path))

        return {
            **result,
            "success": True,
            "filename": original_name,
            "elapsed_time": round(
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
            detail=f"账单分析失败：{exc}",
        ) from exc

    finally:
        remove_files(saved_path)


@router.post("/utilization")
async def analyze_utilization_file(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    start_time = time.perf_counter()
    saved_path: Path | None = None
    original_name = file.filename or "unknown.csv"

    try:
        saved_path = save_csv_upload(
            upload=file,
            prefix="utilization",
        )

        result = analyze_utilization(str(saved_path))

        return {
            **result,
            "success": True,
            "filename": original_name,
            "elapsed_time": round(
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
            detail=f"资源利用率分析失败：{exc}",
        ) from exc

    finally:
        remove_files(saved_path)