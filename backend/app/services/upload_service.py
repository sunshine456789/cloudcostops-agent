from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from backend.config import DATA_DIR


UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_csv_upload(
    upload: UploadFile,
    prefix: str,
) -> Path:
    """校验并保存上传的 CSV 文件。"""

    if not upload.filename:
        raise HTTPException(
            status_code=400,
            detail="上传文件缺少文件名。",
        )

    original_name = Path(upload.filename).name

    if Path(original_name).suffix.lower() != ".csv":
        raise HTTPException(
            status_code=415,
            detail="当前接口仅支持 CSV 文件。",
        )

    unique_name = (
        f"{prefix}_{uuid.uuid4().hex[:12]}_{original_name}"
    )
    save_path = UPLOAD_DIR / unique_name

    try:
        upload.file.seek(0)

        with save_path.open("wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"保存上传文件失败：{exc}",
        ) from exc

    return save_path


def remove_files(*paths: Path | None) -> None:
    """删除本次请求产生的临时文件。"""

    for path in paths:
        if path is None:
            continue

        try:
            path.unlink(missing_ok=True)
        except OSError:
            # 清理失败不应覆盖主要业务结果
            pass