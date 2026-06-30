from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import time

from backend.config import DATA_DIR
from backend.cost_analyzer import analyze_billing

app = FastAPI(
    title="CloudCostOps Agent API",
    description="Cloud Cost Optimization and Resource Governance Agent",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "CloudCostOps Agent API is running.",
        "version": "0.1.0"
    }


@app.post("/analyze/billing")
async def analyze_billing_file(file: UploadFile = File(...)):
    start_time = time.time()

    if not file.filename.endswith(".csv"):
        return {
            "success": False,
            "message": "当前版本仅支持 CSV 文件。"
        }

    save_path = DATA_DIR / file.filename

    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

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