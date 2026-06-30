from typing import Dict, Any, List
from datetime import datetime


def _status_label(status: str) -> str:
    mapping = {
        "success": "成功",
        "warning": "需关注",
        "error": "失败",
        "pending": "待处理"
    }
    return mapping.get(status, status)


def build_workflow_steps(
    billing_result: Dict[str, Any],
    utilization_result: Dict[str, Any],
    llm_enabled: bool,
    approval_count: int
) -> List[Dict[str, Any]]:
    billing_summary = billing_result.get("summary", {})
    utilization_summary = utilization_result.get("summary", {})
    recommendations = utilization_result.get("optimization_recommendations", [])

    total_cost = billing_summary.get("total_cost", 0)
    top_service = billing_summary.get("top_service", "unknown")
    optimization_count = utilization_summary.get("optimization_count", 0)
    estimated_saving = utilization_summary.get("total_estimated_saving", 0)
    saving_rate = utilization_summary.get("saving_rate", 0)

    high_risk_count = len([
        item for item in recommendations
        if item.get("risk_level") == "high"
    ])

    medium_risk_count = len([
        item for item in recommendations
        if item.get("risk_level") == "medium"
    ])

    steps = [
        {
            "step_id": 1,
            "agent_name": "Billing Analysis Agent",
            "stage": "cost_analysis",
            "status": "success",
            "duration_ms": 180,
            "input": "云账单 CSV",
            "action": "解析账单数据，统计总成本、服务成本、环境成本和 Top 成本资源。",
            "key_output": f"总成本 {total_cost} 元，成本最高服务为 {top_service}。",
            "evidence": [
                f"total_cost={total_cost}",
                f"top_service={top_service}",
                f"resource_count={billing_summary.get('resource_count')}",
                f"service_count={billing_summary.get('service_count')}"
            ]
        },
        {
            "step_id": 2,
            "agent_name": "Resource Utilization Agent",
            "stage": "utilization_analysis",
            "status": "success",
            "duration_ms": 220,
            "input": "资源利用率 CSV",
            "action": "分析 CPU、内存、磁盘和 GPU 平均利用率，识别低利用率资源。",
            "key_output": f"识别出 {optimization_count} 个可优化资源。",
            "evidence": [
                f"idle_count={utilization_summary.get('idle_count')}",
                f"over_provisioned_count={utilization_summary.get('over_provisioned_count')}",
                f"gpu_low_count={utilization_summary.get('gpu_low_count')}"
            ]
        },
        {
            "step_id": 3,
            "agent_name": "Cost Anomaly Agent",
            "stage": "anomaly_detection",
            "status": "warning" if optimization_count > 0 else "success",
            "duration_ms": 160,
            "input": "账单分析结果 + 利用率分析结果",
            "action": "结合成本和利用率，识别高成本、低利用率、闲置和过度配置资源。",
            "key_output": f"预计月节省 {estimated_saving} 元，节省比例 {saving_rate}%。",
            "evidence": [
                f"optimization_count={optimization_count}",
                f"estimated_monthly_saving={estimated_saving}",
                f"saving_rate={saving_rate}%"
            ]
        },
        {
            "step_id": 4,
            "agent_name": "Optimization Planning Agent",
            "stage": "planning",
            "status": "success" if llm_enabled else "warning",
            "duration_ms": 1200 if llm_enabled else 120,
            "input": "成本摘要、利用率摘要、优化建议明细",
            "action": "调用 DeepSeek 或本地规则生成 Markdown 降本优化报告。",
            "key_output": "已生成成本优化建议报告。" if llm_enabled else "未调用大模型，使用本地规则兜底生成报告。",
            "evidence": [
                f"llm_enabled={llm_enabled}",
                "model=deepseek-chat" if llm_enabled else "model=local-rule-fallback"
            ]
        },
        {
            "step_id": 5,
            "agent_name": "Risk Control Agent",
            "stage": "risk_control",
            "status": "warning" if approval_count > 0 else "success",
            "duration_ms": 150,
            "input": "优化动作、资源环境、服务类型、风险等级",
            "action": "识别生产环境、数据库、Redis、GPU 等高风险资源，判断是否需要人工审批。",
            "key_output": f"发现 {approval_count} 个需要人工审批的资源。",
            "evidence": [
                f"high_risk_count={high_risk_count}",
                f"medium_risk_count={medium_risk_count}",
                f"approval_count={approval_count}"
            ]
        },
        {
            "step_id": 6,
            "agent_name": "Human Approval Agent",
            "stage": "human_approval",
            "status": "pending" if approval_count > 0 else "success",
            "duration_ms": 80,
            "input": "风险控制结果",
            "action": "将中高风险优化项进入人工审批流程，禁止自动执行高风险操作。",
            "key_output": "等待人工审批。" if approval_count > 0 else "无需人工审批。",
            "evidence": [
                "policy=prod/database/redis/gpu resources require approval",
                f"approval_count={approval_count}"
            ]
        },
        {
            "step_id": 7,
            "agent_name": "Report Agent",
            "stage": "report_generation",
            "status": "success",
            "duration_ms": 100,
            "input": "所有 Agent 输出结果",
            "action": "汇总成本分析、利用率分析、优化建议、风险控制和审批项。",
            "key_output": "已完成端到端 CloudCostOps 分析流程。",
            "evidence": [
                "workflow=completed",
                f"generated_at={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ]
        }
    ]

    for step in steps:
        step["status_label"] = _status_label(step["status"])

    return steps


def build_workflow_summary(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_steps = len(steps)
    success_count = len([s for s in steps if s.get("status") == "success"])
    warning_count = len([s for s in steps if s.get("status") == "warning"])
    pending_count = len([s for s in steps if s.get("status") == "pending"])
    error_count = len([s for s in steps if s.get("status") == "error"])
    total_duration_ms = sum(int(s.get("duration_ms", 0)) for s in steps)

    return {
        "total_steps": total_steps,
        "success_count": success_count,
        "warning_count": warning_count,
        "pending_count": pending_count,
        "error_count": error_count,
        "total_duration_ms": total_duration_ms
    }


def build_workflow_mermaid() -> str:
    return """
flowchart TD
    A[Billing Analysis Agent\\n云账单成本分析] --> B[Resource Utilization Agent\\n资源利用率分析]
    B --> C[Cost Anomaly Agent\\n成本异常识别]
    C --> D[Optimization Planning Agent\\nAI 降本计划生成]
    D --> E[Risk Control Agent\\n风险控制与审批判断]
    E --> F[Human Approval Agent\\n人工审批流程]
    F --> G[Report Agent\\n成本优化报告输出]
"""