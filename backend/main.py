from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import shutil
import time

from backend.config import DATA_DIR
from backend.cost_analyzer import analyze_billing
from backend.utilization_analyzer import analyze_utilization
from backend.optimization_agent import generate_optimization_plan
from backend.audit_logger import log_approval_decision

app = FastAPI(
    title="CloudCostOps Agent API",
    description="Cloud Cost Optimization and Resource Governance Agent",
    version="0.5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApprovalDecision(BaseModel):
    run_id: str
    decision: str
    operator: str = "demo_user"
    comment: Optional[str] = ""
    approved_scope: Optional[str] = "low_risk_only"


@app.get("/")
def root():
    return {
        "message": "CloudCostOps Agent API is running.",
        "version": "0.5.0"
    }


def _save_upload_file(file: UploadFile):
    save_path = DATA_DIR / file.filename

    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return save_path


@app.post("/analyze/billing")
async def analyze_billing_file(file: UploadFile = File(...)):
    start_time = time.time()

    if not file.filename.endswith(".csv"):
        return {
            "success": False,
            "message": "当前版本仅支持 CSV 文件。"
        }

    save_path = _save_upload_file(file)

    try:
        result = analyze_billing(str(save_path))
        result["success"] = True
        result["filename"] = file.filename
        result["elapsed_time"] = round(time.time() - start_time, 3)
        return result

    except Exception as e:
        return {
            "success": False,
            "filename": file.filename,
            "message": "账单分析失败。",
            "error": str(e),
            "elapsed_time": round(time.time() - start_time, 3)
        }


@app.post("/analyze/utilization")
async def analyze_utilization_file(file: UploadFile = File(...)):
    start_time = time.time()

    if not file.filename.endswith(".csv"):
        return {
            "success": False,
            "message": "当前版本仅支持 CSV 文件。"
        }

    save_path = _save_upload_file(file)

    try:
        result = analyze_utilization(str(save_path))
        result["success"] = True
        result["filename"] = file.filename
        result["elapsed_time"] = round(time.time() - start_time, 3)
        return result

    except Exception as e:
        return {
            "success": False,
            "filename": file.filename,
            "message": "资源利用率分析失败。",
            "error": str(e),
            "elapsed_time": round(time.time() - start_time, 3)
        }


@app.post("/agent/optimization-plan")
async def generate_plan(
    billing_file: UploadFile = File(...),
    utilization_file: UploadFile = File(...)
):
    start_time = time.time()

    if not billing_file.filename.endswith(".csv"):
        return {
            "success": False,
            "message": "云账单文件必须是 CSV。"
        }

    if not utilization_file.filename.endswith(".csv"):
        return {
            "success": False,
            "message": "资源利用率文件必须是 CSV。"
        }

    try:
        billing_path = _save_upload_file(billing_file)
        utilization_path = _save_upload_file(utilization_file)

        billing_result = analyze_billing(str(billing_path))
        utilization_result = analyze_utilization(str(utilization_path))

        agent_result = generate_optimization_plan(
            billing_result=billing_result,
            utilization_result=utilization_result
        )

        agent_result["billing_filename"] = billing_file.filename
        agent_result["utilization_filename"] = utilization_file.filename
        agent_result["total_elapsed_time"] = round(time.time() - start_time, 3)

        return agent_result

    except Exception as e:
        return {
            "success": False,
            "message": "生成成本优化建议失败。",
            "error": str(e),
            "total_elapsed_time": round(time.time() - start_time, 3)
        }


@app.post("/agent/approval-decision")
async def submit_approval_decision(decision: ApprovalDecision):
    try:
        result = log_approval_decision(decision.model_dump())
        return result
    except Exception as e:
        return {
            "success": False,
            "message": "审批决策记录失败。",
            "error": str(e)
        }