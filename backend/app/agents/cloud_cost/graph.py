from __future__ import annotations

from typing import Any, Literal

import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from langgraph.graph import (
    END,
    START,
    StateGraph,
)
from langgraph.types import Command

from backend.app.agents.cloud_cost.nodes import (
    approval_gate_node,
    billing_analysis_node,
    completed_node,
    human_approval_node,
    optimization_planning_node,
    rejected_node,
    risk_assessment_node,
    utilization_analysis_node,
    validate_data_node,
)
from backend.app.agents.cloud_cost.state import (
    CloudCostState,
)
from backend.audit_logger import (
    generate_id,
    log_agent_run,
)
from backend.workflow_trace import (
    build_workflow_summary,
)


def route_after_planning(
    state: CloudCostState,
) -> Literal[
    "approval_gate",
    "completed",
]:
    """
    优化规划结束后，根据风险结果决定
    是否进入人工审批。
    """

    if state.get(
        "approval_required",
        False,
    ):
        return "approval_gate"

    return "completed"


def route_after_approval(
    state: CloudCostState,
) -> Literal[
    "completed",
    "rejected",
]:
    """根据人工审批结果继续或终止。"""

    if (
        state.get("approval_decision")
        == "approve"
    ):
        return "completed"

    return "rejected"


builder = StateGraph(
    CloudCostState
)

builder.add_node(
    "validate_data",
    validate_data_node,
)

builder.add_node(
    "billing_analysis",
    billing_analysis_node,
)

builder.add_node(
    "utilization_analysis",
    utilization_analysis_node,
)

builder.add_node(
    "risk_assessment",
    risk_assessment_node,
)

builder.add_node(
    "optimization_planning",
    optimization_planning_node,
)

builder.add_node(
    "approval_gate",
    approval_gate_node,
)

builder.add_node(
    "human_approval",
    human_approval_node,
)

builder.add_node(
    "completed",
    completed_node,
)

builder.add_node(
    "rejected",
    rejected_node,
)


# ==============================
# 正常执行链
# ==============================

builder.add_edge(
    START,
    "validate_data",
)

builder.add_edge(
    "validate_data",
    "billing_analysis",
)

builder.add_edge(
    "billing_analysis",
    "utilization_analysis",
)

builder.add_edge(
    "utilization_analysis",
    "risk_assessment",
)

builder.add_edge(
    "risk_assessment",
    "optimization_planning",
)


# ==============================
# 是否需要人工审批
# ==============================

builder.add_conditional_edges(
    "optimization_planning",
    route_after_planning,
    {
        "approval_gate": (
            "approval_gate"
        ),
        "completed": (
            "completed"
        ),
    },
)


# ==============================
# 真正 Human-in-the-loop
# ==============================

builder.add_edge(
    "approval_gate",
    "human_approval",
)

builder.add_conditional_edges(
    "human_approval",
    route_after_approval,
    {
        "completed": (
            "completed"
        ),
        "rejected": (
            "rejected"
        ),
    },
)


# ==============================
# END
# ==============================

builder.add_edge(
    "completed",
    END,
)

builder.add_edge(
    "rejected",
    END,
)


# ============================================================
# LangGraph 持久化 Checkpoint
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

RUNTIME_DIR = PROJECT_ROOT / "runtime"
RUNTIME_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

CHECKPOINT_DB_PATH = (
    RUNTIME_DIR
    / "langgraph_checkpoints.sqlite"
)


# check_same_thread=False：
# FastAPI 请求可能由不同工作线程处理。
# SqliteSaver 内部使用锁保证自身操作安全。
checkpoint_connection = sqlite3.connect(
    str(CHECKPOINT_DB_PATH),
    check_same_thread=False,
)


checkpointer = SqliteSaver(
    checkpoint_connection
)


cloud_cost_graph = builder.compile(
    checkpointer=checkpointer
)

WORKFLOW_MERMAID = """
flowchart TD
    A[Data Validation Agent]
    --> B[Billing Analysis Agent]
    B --> C[Resource Utilization Agent]
    C --> D[Risk Control Agent]
    D --> E[Optimization Planning Agent]

    E -->|无需审批| H[Workflow Completed]
    E -->|高风险| F[Human Approval]

    F -->|Approve| H
    F -->|Reject| I[Workflow Rejected]
"""


def _extract_interrupt_payloads(
    graph_result: dict[str, Any],
) -> list[Any]:
    """
    将 LangGraph Interrupt 对象转换为
    FastAPI 可以 JSON 序列化的数据。
    """

    raw_interrupts = graph_result.get(
        "__interrupt__",
        (),
    )

    payloads: list[Any] = []

    for item in raw_interrupts:
        value = getattr(
            item,
            "value",
            item,
        )
        payloads.append(value)

    return payloads


def _build_result(
    state: dict[str, Any],
    *,
    run_id: str,
    interrupts: list[Any] | None = None,
) -> dict[str, Any]:
    """
    将 LangGraph State 转换为 API 返回结果。
    """

    workflow_steps = state.get(
        "workflow_steps",
        [],
    )

    workflow_summary = (
        build_workflow_summary(
            workflow_steps
        )
    )

    plan_result = dict(
        state.get(
            "plan_result",
            {},
        )
    )

    result = {
        **plan_result,

        "success": True,

        "run_id": run_id,
        "thread_id": run_id,

        "workflow_engine": (
            "langgraph"
        ),

        "status": state.get(
            "status",
            "unknown",
        ),

        "approval_required": (
            state.get(
                "approval_required",
                False,
            )
        ),

        "approval_items": state.get(
            "approval_items",
            [],
        ),

        "approval_count": len(
            state.get(
                "approval_items",
                [],
            )
        ),

        "max_risk_level": state.get(
            "max_risk_level",
            "low",
        ),

        "approval_decision": (
            state.get(
                "approval_decision"
            )
        ),

        "approval_operator": (
            state.get(
                "approval_operator"
            )
        ),

        "approved_scope": (
            state.get(
                "approved_scope"
            )
        ),

        "workflow_steps": (
            workflow_steps
        ),

        "workflow_summary": (
            workflow_summary
        ),

        "workflow_mermaid": (
            WORKFLOW_MERMAID
        ),

        "interrupts": (
            interrupts or []
        ),
    }

    return result


def _log_workflow_result(
    result: dict[str, Any],
) -> None:
    """记录一次工作流状态快照。"""

    log_agent_run({
        "run_id": result.get(
            "run_id"
        ),
        "workflow_engine": (
            "langgraph"
        ),
        "status": result.get(
            "status"
        ),
        "approval_count": (
            result.get(
                "approval_count",
                0,
            )
        ),
        "approval_decision": (
            result.get(
                "approval_decision"
            )
        ),
        "estimated_monthly_saving": (
            result.get(
                "estimated_monthly_saving",
                0,
            )
        ),
        "saving_rate": (
            result.get(
                "saving_rate",
                0,
            )
        ),
        "report_id": (
            result.get(
                "report_id"
            )
        ),
        "workflow_summary": (
            result.get(
                "workflow_summary",
                {},
            )
        ),
    })


def run_cloud_cost_graph(
    billing_path: str,
    utilization_path: str,
) -> dict[str, Any]:
    """
    创建并执行新的 CloudCostOps 工作流。

    如果遇到 interrupt()，
    函数会返回 pending_approval，
    而不是继续执行。
    """

    run_id = generate_id(
        "run"
    )

    initial_state: CloudCostState = {
        "run_id": run_id,

        "billing_path": (
            billing_path
        ),

        "utilization_path": (
            utilization_path
        ),

        "workflow_steps": [],

        "status": "running",
    }

    config = {
        "configurable": {
            "thread_id": run_id,
        }
    }

    graph_result = (
        cloud_cost_graph.invoke(
            initial_state,
            config=config,
        )
    )

    interrupts = (
        _extract_interrupt_payloads(
            graph_result
        )
    )

    snapshot = (
        cloud_cost_graph.get_state(
            config
        )
    )

    state = dict(
        snapshot.values
    )

    if interrupts:
        state["status"] = (
            "pending_approval"
        )

    result = _build_result(
        state,
        run_id=run_id,
        interrupts=interrupts,
    )

    _log_workflow_result(
        result
    )

    return result


def resume_cloud_cost_graph(
    run_id: str,
    approval_payload: dict[str, Any],
) -> dict[str, Any]:
    """
    使用原 thread_id 恢复暂停的工作流。
    """

    config = {
        "configurable": {
            "thread_id": run_id,
        }
    }

    snapshot = (
        cloud_cost_graph.get_state(
            config
        )
    )

    if not snapshot.values:
        raise ValueError(
            f"找不到运行记录：{run_id}。"
            "如果服务已经重启，"
            "InMemorySaver 中的 checkpoint "
            "也会丢失。"
        )

    if not snapshot.next:
        raise ValueError(
            f"工作流 {run_id} "
            "当前没有处于暂停状态。"
        )

    graph_result = (
        cloud_cost_graph.invoke(
            Command(
                resume=approval_payload
            ),
            config=config,
        )
    )

    interrupts = (
        _extract_interrupt_payloads(
            graph_result
        )
    )

    final_snapshot = (
        cloud_cost_graph.get_state(
            config
        )
    )

    state = dict(
        final_snapshot.values
    )

    result = _build_result(
        state,
        run_id=run_id,
        interrupts=interrupts,
    )

    _log_workflow_result(
        result
    )

    return result