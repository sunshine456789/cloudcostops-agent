from typing import Dict, Any, List
import pandas as pd
import numpy as np


REQUIRED_COLUMNS = [
    "date",
    "resource_id",
    "service",
    "env",
    "owner",
    "region",
    "cpu_utilization",
    "memory_utilization",
    "disk_utilization",
    "gpu_utilization",
    "monthly_cost"
]


def _to_builtin(obj):
    if isinstance(obj, dict):
        return {k: _to_builtin(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_builtin(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if pd.isna(obj):
        return None
    return obj


def load_utilization_csv(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"CSV 缺少必要字段：{missing_cols}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    numeric_cols = [
        "cpu_utilization",
        "memory_utilization",
        "disk_utilization",
        "gpu_utilization",
        "monthly_cost"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = df.dropna(subset=["date"])

    return df


def get_risk_level(row: pd.Series, action: str) -> str:
    env = str(row.get("env", "")).lower()
    service = str(row.get("service", "")).lower()

    if env == "prod":
        return "high"

    if service in ["rds", "redis", "mysql", "database"]:
        return "medium"

    if "stop" in action or "release" in action:
        return "medium" if env != "test" else "low"

    return "low"


def build_recommendation(row: pd.Series) -> Dict[str, Any]:
    service = str(row["service"])
    env = str(row["env"])

    avg_cpu = float(row["avg_cpu_utilization"])
    avg_memory = float(row["avg_memory_utilization"])
    avg_disk = float(row["avg_disk_utilization"])
    avg_gpu = float(row["avg_gpu_utilization"])
    monthly_cost = float(row["monthly_cost"])

    issue_type = "normal"
    action = "keep"
    reason = "资源利用率正常，暂不建议调整。"
    saving_ratio = 0.0

    if service.upper() == "GPU" and avg_gpu < 15:
        issue_type = "gpu_low_utilization"
        action = "enable_scheduled_shutdown"
        reason = "GPU 平均利用率低于 15%，建议设置训练任务定时启停或按需释放。"
        saving_ratio = 0.50

    elif avg_cpu < 8 and avg_memory < 20:
        issue_type = "idle_resource"
        action = "stop_or_release"
        reason = "CPU 和内存长期处于低利用率，疑似闲置资源，建议停机或释放。"
        saving_ratio = 0.70

    elif avg_cpu < 20 and avg_memory < 40:
        issue_type = "over_provisioned"
        action = "downsize_instance"
        reason = "CPU 和内存利用率偏低，疑似规格过高，建议降配。"
        saving_ratio = 0.35

    elif avg_disk < 20 and service.upper() in ["OSS", "EBS", "DISK"]:
        issue_type = "storage_low_usage"
        action = "optimize_storage_policy"
        reason = "存储利用率偏低，建议检查生命周期策略或归档策略。"
        saving_ratio = 0.25

    estimated_saving = round(monthly_cost * saving_ratio, 2)

    risk_level = get_risk_level(row, action)

    return {
        "resource_id": row["resource_id"],
        "service": service,
        "env": env,
        "owner": row["owner"],
        "region": row["region"],
        "avg_cpu_utilization": round(avg_cpu, 2),
        "avg_memory_utilization": round(avg_memory, 2),
        "avg_disk_utilization": round(avg_disk, 2),
        "avg_gpu_utilization": round(avg_gpu, 2),
        "monthly_cost": round(monthly_cost, 2),
        "issue_type": issue_type,
        "recommend_action": action,
        "estimated_monthly_saving": estimated_saving,
        "risk_level": risk_level,
        "need_human_approval": risk_level in ["medium", "high"],
        "reason": reason
    }


def analyze_utilization(file_path: str) -> Dict[str, Any]:
    df = load_utilization_csv(file_path)

    resource_profile = (
        df.groupby(["resource_id", "service", "env", "owner", "region"])
        .agg(
            avg_cpu_utilization=("cpu_utilization", "mean"),
            avg_memory_utilization=("memory_utilization", "mean"),
            avg_disk_utilization=("disk_utilization", "mean"),
            avg_gpu_utilization=("gpu_utilization", "mean"),
            monthly_cost=("monthly_cost", "max"),
            sample_days=("date", "nunique")
        )
        .reset_index()
    )

    recommendations: List[Dict[str, Any]] = []

    for _, row in resource_profile.iterrows():
        rec = build_recommendation(row)
        if rec["issue_type"] != "normal":
            recommendations.append(rec)

    recommendations = sorted(
        recommendations,
        key=lambda x: x["estimated_monthly_saving"],
        reverse=True
    )

    total_monthly_cost = round(float(resource_profile["monthly_cost"].sum()), 2)
    total_estimated_saving = round(
        float(sum(item["estimated_monthly_saving"] for item in recommendations)),
        2
    )

    idle_count = len([x for x in recommendations if x["issue_type"] == "idle_resource"])
    over_provisioned_count = len([x for x in recommendations if x["issue_type"] == "over_provisioned"])
    gpu_low_count = len([x for x in recommendations if x["issue_type"] == "gpu_low_utilization"])

    service_utilization = (
        resource_profile.groupby("service")
        .agg(
            avg_cpu_utilization=("avg_cpu_utilization", "mean"),
            avg_memory_utilization=("avg_memory_utilization", "mean"),
            avg_gpu_utilization=("avg_gpu_utilization", "mean"),
            monthly_cost=("monthly_cost", "sum")
        )
        .reset_index()
    )

    for col in [
        "avg_cpu_utilization",
        "avg_memory_utilization",
        "avg_gpu_utilization",
        "monthly_cost"
    ]:
        service_utilization[col] = service_utilization[col].round(2)

    env_utilization = (
        resource_profile.groupby("env")
        .agg(
            resource_count=("resource_id", "count"),
            avg_cpu_utilization=("avg_cpu_utilization", "mean"),
            avg_memory_utilization=("avg_memory_utilization", "mean"),
            monthly_cost=("monthly_cost", "sum")
        )
        .reset_index()
    )

    for col in ["avg_cpu_utilization", "avg_memory_utilization", "monthly_cost"]:
        env_utilization[col] = env_utilization[col].round(2)

    resource_profile_display = resource_profile.copy()

    for col in [
        "avg_cpu_utilization",
        "avg_memory_utilization",
        "avg_disk_utilization",
        "avg_gpu_utilization",
        "monthly_cost"
    ]:
        resource_profile_display[col] = resource_profile_display[col].round(2)

    summary = {
        "resource_count": int(resource_profile["resource_id"].nunique()),
        "total_monthly_cost": total_monthly_cost,
        "optimization_count": len(recommendations),
        "idle_count": idle_count,
        "over_provisioned_count": over_provisioned_count,
        "gpu_low_count": gpu_low_count,
        "total_estimated_saving": total_estimated_saving,
        "saving_rate": round(total_estimated_saving / total_monthly_cost * 100, 2)
        if total_monthly_cost > 0 else 0
    }

    result = {
        "summary": summary,
        "resource_profile": resource_profile_display.to_dict(orient="records"),
        "service_utilization": service_utilization.to_dict(orient="records"),
        "env_utilization": env_utilization.to_dict(orient="records"),
        "optimization_recommendations": recommendations,
        "analysis_comment": build_utilization_comment(summary, recommendations)
    }

    return _to_builtin(result)


def build_utilization_comment(
    summary: Dict[str, Any],
    recommendations: List[Dict[str, Any]]
) -> str:
    lines = []

    lines.append(
        f"本次共分析 {summary['resource_count']} 个云资源，月度成本合计 "
        f"{summary['total_monthly_cost']} 元。"
    )

    lines.append(
        f"系统识别出 {summary['optimization_count']} 个可优化资源，预计每月可节省 "
        f"{summary['total_estimated_saving']} 元，节省比例约为 {summary['saving_rate']}%。"
    )

    if summary["idle_count"] > 0:
        lines.append(f"其中包含 {summary['idle_count']} 个疑似闲置资源，建议优先处理。")

    if summary["over_provisioned_count"] > 0:
        lines.append(f"其中包含 {summary['over_provisioned_count']} 个疑似过度配置资源，建议评估降配。")

    if summary["gpu_low_count"] > 0:
        lines.append(f"其中包含 {summary['gpu_low_count']} 个 GPU 低利用率资源，建议设置定时启停策略。")

    high_risk_items = [x for x in recommendations if x["risk_level"] == "high"]

    if high_risk_items:
        lines.append("检测到生产环境资源优化建议，所有高风险操作必须经过人工审批。")
    else:
        lines.append("当前优化建议以低中风险为主，可进入人工确认流程。")

    return "\n".join(lines)