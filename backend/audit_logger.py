from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json
import uuid

from backend.config import LOG_DIR, OUTPUT_DIR


REPORT_DIR = OUTPUT_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_id(prefix: str) -> str:
    short_id = uuid.uuid4().hex[:8]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}_{short_id}"


def append_jsonl(filename: str, record: Dict[str, Any]) -> Path:
    LOG_DIR.mkdir(exist_ok=True)
    file_path = LOG_DIR / filename

    record = {
        "created_at": now_str(),
        **record
    }

    with file_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return file_path


def save_markdown_report(
    markdown_report: str,
    report_id: Optional[str] = None
) -> Dict[str, Any]:
    if not report_id:
        report_id = generate_id("report")

    filename = f"{report_id}.md"
    file_path = REPORT_DIR / filename

    with file_path.open("w", encoding="utf-8") as f:
        f.write(markdown_report)

    return {
        "report_id": report_id,
        "report_filename": filename,
        "report_path": str(file_path),
        "report_saved": True
    }


def log_agent_run(record: Dict[str, Any]) -> None:
    append_jsonl("agent_runs.jsonl", record)


def log_approval_decision(record: Dict[str, Any]) -> Dict[str, Any]:
    approval_id = generate_id("approval")

    payload = {
        "approval_id": approval_id,
        **record
    }

    append_jsonl("approval_decisions.jsonl", payload)

    return {
        "success": True,
        "approval_id": approval_id,
        "message": "审批决策已写入审计日志。"
    }