from __future__ import annotations

from typing import Any, Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from backend.app.agents.cloud_cost.nodes import (
    billing_analysis_node,
    completed_node,
    optimization_planning_node,
    pending_approval_node,
    risk_assessment_node,
    utilization_analysis_node,
    validate_data_node,
)
from backend.app.agents.cloud_cost.state import CloudCostState
from backend.audit_logger import (
    generate_id,
    log_agent_run,
)
from backend.workflow_trace import build_workflow_summary


def route_after_planning(
    state: CloudCostState,
) -> Literal["pending_approval", "completed"]:
    if state.get("approval_required"):
        return "pending_approval"

    return "completed"


builder = StateGraph(CloudCostState)

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
    "pending_approval",
    pending_approval_node,
)
builder.add_node(
    "completed",
    completed_node,
)

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

builder.add_conditional_edges(
    "optimization_planning",
    route_after_planning,
    {
        "pending_approval": "pending_approval",
        "completed": "completed",
    },
)

builder.add_edge(
    "pending_approval",
    END,
)
builder.add_edge(
    "completed",
    END,
)

checkpointer = InMemorySaver()

cloud_cost_graph = builder.compile(
    checkpointer=checkpointer
)


WORKFLOW_MERMAID = """
flowchart TD
    A[Data Validation Agent] --> B[Billing Analysis Agent]
    B --> C[Resource Utilization Agent]
    C --> D[Risk Control Agent]
    D --> E[Optimization Planning Agent]
    E -->|需要审批| F[Human Approval Agent]
    E -->|无需审批| G[Workflow Completed]
"""


def run_cloud_cost_graph(
    billing_path: str,
    utilization_path: str,
) -> dict[str, Any]:
    """执行一次真正的 LangGraph 成本治理工作流。"""

    run_id = generate_id("run")

    initial_state: CloudCostState = {
        "run_id": run_id,
        "billing_path": billing_path,
        "utilization_path": utilization_path,
        "workflow_steps": [],
        "status": "running",
    }

    config = {
        "configurable": {
            "thread_id": run_id,
        }
    }

    final_state = cloud_cost_graph.invoke(
        initial_state,
        config=config,
    )

    workflow_steps = final_state.get(
        "workflow_steps",
        [],
    )
    workflow_summary = build_workflow_summary(
        workflow_steps
    )

    plan_result = dict(
        final_state.get("plan_result", {})
    )

    result = {
        **plan_result,
        "success": True,
        "run_id": run_id,
        "thread_id": run_id,
        "workflow_engine": "langgraph",
        "status": final_state.get(
            "status",
            "completed",
        ),
        "approval_required": final_state.get(
            "approval_required",
            False,
        ),
        "approval_items": final_state.get(
            "approval_items",
            [],
        ),
        "approval_count": len(
            final_state.get("approval_items", [])
        ),
        "max_risk_level": final_state.get(
            "max_risk_level",
            "low",
        ),
        "workflow_steps": workflow_steps,
        "workflow_summary": workflow_summary,
        "workflow_mermaid": WORKFLOW_MERMAID,
    }

    log_agent_run({
        "run_id": run_id,
        "workflow_engine": "langgraph",
        "status": result["status"],
        "approval_count": result["approval_count"],
        "estimated_monthly_saving": result.get(
            "estimated_monthly_saving",
            0,
        ),
        "saving_rate": result.get(
            "saving_rate",
            0,
        ),
        "report_id": result.get("report_id"),
        "workflow_summary": workflow_summary,
    })

    return result