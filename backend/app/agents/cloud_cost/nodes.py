from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from backend.app.agents.cloud_cost.state import CloudCostState
from backend.cost_analyzer import analyze_billing
from backend.optimization_agent import generate_optimization_plan
from backend.utilization_analyzer import analyze_utilization


def _append_step(
    state: CloudCostState,
    *,
    agent_name: str,
    stage: str,
    status: str,
    duration_ms: int,
    action: str,
    key_output: str,
    evidence: list[str] | None = None,
) -> list[dict[str, Any]]:
    """向执行轨迹中追加真实节点记录。"""

    steps = list(state.get("workflow_steps", []))

    status_labels = {
        "success": "成功",
        "warning": "需关注",
        "pending": "待审批",
        "error": "失败",
    }

    steps.append({
        "step_id": len(steps) + 1,
        "agent_name": agent_name,
        "stage": stage,
        "status": status,
        "status_label": status_labels.get(status, status),
        "duration_ms": duration_ms,
        "action": action,
        "key_output": key_output,
        "evidence": evidence or [],
    })

    return steps


def validate_data_node(
    state: CloudCostState,
) -> dict[str, Any]:
    """检查输入文件是否存在且为 CSV。"""

    started = time.perf_counter()

    billing_path = Path(state["billing_path"])
    utilization_path = Path(state["utilization_path"])

    for path, label in (
        (billing_path, "账单文件"),
        (utilization_path, "利用率文件"),
    ):
        if not path.exists():
            raise ValueError(f"{label}不存在：{path}")

        if path.suffix.lower() != ".csv":
            raise ValueError(f"{label}必须是 CSV：{path.name}")

    duration_ms = round(
        (time.perf_counter() - started) * 1000
    )

    return {
        "workflow_steps": _append_step(
            state,
            agent_name="Data Validation Agent",
            stage="data_validation",
            status="success",
            duration_ms=duration_ms,
            action="校验上传文件路径、格式和可访问性。",
            key_output="账单文件和利用率文件均通过校验。",
            evidence=[
                f"billing_file={billing_path.name}",
                f"utilization_file={utilization_path.name}",
            ],
        )
    }


def billing_analysis_node(
    state: CloudCostState,
) -> dict[str, Any]:
    """执行真实的账单成本分析。"""

    started = time.perf_counter()

    result = analyze_billing(
        state["billing_path"]
    )

    duration_ms = round(
        (time.perf_counter() - started) * 1000
    )

    summary = result.get("summary", {})

    return {
        "billing_result": result,
        "workflow_steps": _append_step(
            state,
            agent_name="Billing Analysis Agent",
            stage="cost_analysis",
            status="success",
            duration_ms=duration_ms,
            action=(
                "使用 Pandas 解析账单，统计总成本、"
                "服务成本、环境成本和异常资源。"
            ),
            key_output=(
                f"总成本 {summary.get('total_cost', 0)} 元，"
                f"最高成本服务为 "
                f"{summary.get('top_service', 'unknown')}。"
            ),
            evidence=[
                f"resource_count={summary.get('resource_count', 0)}",
                f"service_count={summary.get('service_count', 0)}",
                f"avg_daily_cost={summary.get('avg_daily_cost', 0)}",
            ],
        ),
    }


def utilization_analysis_node(
    state: CloudCostState,
) -> dict[str, Any]:
    """执行真实的资源利用率分析。"""

    started = time.perf_counter()

    result = analyze_utilization(
        state["utilization_path"]
    )

    duration_ms = round(
        (time.perf_counter() - started) * 1000
    )

    summary = result.get("summary", {})

    return {
        "utilization_result": result,
        "workflow_steps": _append_step(
            state,
            agent_name="Resource Utilization Agent",
            stage="utilization_analysis",
            status="success",
            duration_ms=duration_ms,
            action=(
                "分析 CPU、内存、磁盘和 GPU 利用率，"
                "识别闲置、过度配置和 GPU 低利用率资源。"
            ),
            key_output=(
                f"识别出 "
                f"{summary.get('optimization_count', 0)} "
                "个可优化资源。"
            ),
            evidence=[
                f"idle_count={summary.get('idle_count', 0)}",
                (
                    "over_provisioned_count="
                    f"{summary.get('over_provisioned_count', 0)}"
                ),
                f"gpu_low_count={summary.get('gpu_low_count', 0)}",
                (
                    "estimated_saving="
                    f"{summary.get('total_estimated_saving', 0)}"
                ),
            ],
        ),
    }


def risk_assessment_node(
    state: CloudCostState,
) -> dict[str, Any]:
    """依据优化项风险等级决定是否需要审批。"""

    started = time.perf_counter()

    recommendations = state[
        "utilization_result"
    ].get("optimization_recommendations", [])

    approval_items = [
        item
        for item in recommendations
        if item.get("need_human_approval")
    ]

    risk_order = {
        "low": 1,
        "medium": 2,
        "high": 3,
    }

    max_risk_level = "low"

    for item in recommendations:
        current = str(
            item.get("risk_level", "low")
        ).lower()

        if risk_order.get(current, 0) > risk_order.get(
            max_risk_level,
            0,
        ):
            max_risk_level = current

    approval_required = len(approval_items) > 0

    duration_ms = round(
        (time.perf_counter() - started) * 1000
    )

    return {
        "approval_items": approval_items,
        "approval_required": approval_required,
        "max_risk_level": max_risk_level,
        "workflow_steps": _append_step(
            state,
            agent_name="Risk Control Agent",
            stage="risk_assessment",
            status=(
                "warning"
                if approval_required
                else "success"
            ),
            duration_ms=duration_ms,
            action=(
                "检查生产环境、数据库、Redis、GPU "
                "以及停机释放类动作的风险等级。"
            ),
            key_output=(
                f"发现 {len(approval_items)} "
                "个需要人工审批的优化项。"
            ),
            evidence=[
                f"approval_required={approval_required}",
                f"approval_count={len(approval_items)}",
                f"max_risk_level={max_risk_level}",
            ],
        ),
    }


def optimization_planning_node(
    state: CloudCostState,
) -> dict[str, Any]:
    """调用 DeepSeek 或本地规则生成优化报告。"""

    started = time.perf_counter()

    plan_result = generate_optimization_plan(
        billing_result=state["billing_result"],
        utilization_result=state["utilization_result"],
        run_id=state["run_id"],
        log_run=False,
    )

    duration_ms = round(
        (time.perf_counter() - started) * 1000
    )

    # 丢弃旧版模拟出来的工作流信息，
    # 最终由 LangGraph 的真实执行轨迹替换。
    for key in (
        "workflow_steps",
        "workflow_summary",
        "workflow_mermaid",
    ):
        plan_result.pop(key, None)

    return {
        "plan_result": plan_result,
        "workflow_steps": _append_step(
            state,
            agent_name="Optimization Planning Agent",
            stage="optimization_planning",
            status=(
                "success"
                if plan_result.get("llm_enabled")
                else "warning"
            ),
            duration_ms=duration_ms,
            action=(
                "根据确定性分析结果调用 DeepSeek，"
                "生成成本优化报告。"
            ),
            key_output=(
                "成本优化报告已生成。"
                if plan_result.get("llm_enabled")
                else "大模型不可用，已使用本地规则报告。"
            ),
            evidence=[
                (
                    "llm_enabled="
                    f"{plan_result.get('llm_enabled', False)}"
                ),
                (
                    "llm_model="
                    f"{plan_result.get('llm_model', 'unknown')}"
                ),
            ],
        ),
    }


def pending_approval_node(
    state: CloudCostState,
) -> dict[str, Any]:
    """标记流程进入人工审批状态。"""

    return {
        "status": "pending_approval",
        "workflow_steps": _append_step(
            state,
            agent_name="Human Approval Agent",
            stage="human_approval",
            status="pending",
            duration_ms=0,
            action="暂停自动执行，等待人工审批。",
            key_output=(
                f"{len(state.get('approval_items', []))} "
                "个优化项等待审批。"
            ),
            evidence=[
                f"run_id={state['run_id']}",
                "workflow_status=pending_approval",
            ],
        ),
    }


def completed_node(
    state: CloudCostState,
) -> dict[str, Any]:
    """标记无需审批的任务已经完成。"""

    return {
        "status": "completed",
        "workflow_steps": _append_step(
            state,
            agent_name="Workflow Completion Agent",
            stage="workflow_completion",
            status="success",
            duration_ms=0,
            action="完成所有自动分析与报告生成任务。",
            key_output="本次 CloudCostOps 工作流执行完成。",
            evidence=[
                f"run_id={state['run_id']}",
                "workflow_status=completed",
            ],
        ),
    }