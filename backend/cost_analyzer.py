from typing import Dict, Any
import pandas as pd
import numpy as np


REQUIRED_COLUMNS = [
    "date",
    "service",
    "resource_id",
    "cost",
    "env",
    "owner",
    "region"
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


def load_billing_csv(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"CSV 缺少必要字段：{missing_cols}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["cost"] = pd.to_numeric(df["cost"], errors="coerce").fillna(0)

    df = df.dropna(subset=["date"])

    return df


def analyze_billing(file_path: str) -> Dict[str, Any]:
    df = load_billing_csv(file_path)

    total_cost = round(float(df["cost"].sum()), 2)
    avg_daily_cost = round(float(df.groupby("date")["cost"].sum().mean()), 2)
    record_count = int(len(df))
    resource_count = int(df["resource_id"].nunique())
    service_count = int(df["service"].nunique())

    service_cost = (
        df.groupby("service")["cost"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    service_cost["cost"] = service_cost["cost"].round(2)

    resource_cost = (
        df.groupby(["resource_id", "service", "env", "owner", "region"])["cost"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    resource_cost["cost"] = resource_cost["cost"].round(2)

    daily_cost = (
        df.groupby("date")["cost"]
        .sum()
        .reset_index()
        .sort_values("date")
    )
    daily_cost["date"] = daily_cost["date"].dt.strftime("%Y-%m-%d")
    daily_cost["cost"] = daily_cost["cost"].round(2)

    env_cost = (
        df.groupby("env")["cost"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    env_cost["cost"] = env_cost["cost"].round(2)

    owner_cost = (
        df.groupby("owner")["cost"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    owner_cost["cost"] = owner_cost["cost"].round(2)

    mean_cost = resource_cost["cost"].mean()
    std_cost = resource_cost["cost"].std() if len(resource_cost) > 1 else 0
    threshold = mean_cost + std_cost

    anomaly_resources = resource_cost[resource_cost["cost"] >= threshold].copy()
    anomaly_resources["reason"] = "该资源成本明显高于平均水平，建议重点排查。"

    top_resources = resource_cost.head(10)
    anomaly_resources = anomaly_resources.head(10)

    summary = {
        "total_cost": total_cost,
        "avg_daily_cost": avg_daily_cost,
        "record_count": record_count,
        "resource_count": resource_count,
        "service_count": service_count,
        "top_service": service_cost.iloc[0]["service"] if not service_cost.empty else None,
        "top_service_cost": float(service_cost.iloc[0]["cost"]) if not service_cost.empty else 0,
    }

    result = {
        "summary": summary,
        "daily_cost": daily_cost.to_dict(orient="records"),
        "service_cost": service_cost.to_dict(orient="records"),
        "env_cost": env_cost.to_dict(orient="records"),
        "owner_cost": owner_cost.to_dict(orient="records"),
        "top_resources": top_resources.to_dict(orient="records"),
        "anomaly_resources": anomaly_resources.to_dict(orient="records"),
        "analysis_comment": build_basic_comment(summary, anomaly_resources)
    }

    return _to_builtin(result)


def build_basic_comment(summary: Dict[str, Any], anomaly_resources: pd.DataFrame) -> str:
    comment = []
    comment.append(f"本次账单总成本为 {summary['total_cost']} 元，平均每日成本为 {summary['avg_daily_cost']} 元。")
    comment.append(f"当前共涉及 {summary['service_count']} 类云服务、{summary['resource_count']} 个资源。")

    if summary.get("top_service"):
        comment.append(
            f"成本最高的服务是 {summary['top_service']}，费用为 {summary['top_service_cost']} 元。"
        )

    if len(anomaly_resources) > 0:
        comment.append(f"系统检测到 {len(anomaly_resources)} 个疑似成本异常资源，建议优先排查。")
    else:
        comment.append("当前未检测到明显高于平均水平的成本异常资源。")

    return "\n".join(comment)