from typing import Dict, Any, List
from datetime import datetime

from backend.llm_client import call_llm, has_llm_config
from backend.config import OPENAI_MODEL


def _format_recommendations(recommendations: List[Dict[str, Any]], limit: int = 8) -> str:
    if not recommendations:
        return "当前没有检测到明显可优化资源。"

    lines = []
    for idx, item in enumerate(recommendations[:limit], start=1):
        lines.append(
            f"{idx}. resource_id={item.get('resource_id')}, "
            f"service={item.get('service')}, env={item.get('env')}, "
            f"issue_type={item.get('issue_type')}, "
            f"action={item.get('recommend_action')}, "
            f"monthly_cost={item.get('monthly_cost')}, "
            f"estimated_saving={item.get('estimated_monthly_saving')}, "
            f"risk_level={item.get('risk_level')}, "
            f"need_human_approval={item.get('need_human_approval')}, "
            f"reason={item.get('reason')}"
        )
    return "\n".join(lines)


def _build_prompt(
    billing_result: Dict[str, Any],
    utilization_result: Dict[str, Any]
) -> str:
    billing_summary = billing_result.get("summary", {})
    utilization_summary = utilization_result.get("summary", {})
    recommendations = utilization_result.get("optimization_recommendations", [])

    rec_text = _format_recommendations(recommendations)

    prompt = f"""
你是一个互联网企业内部的 CloudCostOps / FinOps / AIOps 成本治理专家。
请根据云账单分析结果和资源利用率分析结果，生成一份专业、可落地、适合研发和平台团队阅读的云成本优化建议报告。

要求：
1. 不要编造不存在的数据。
2. 所有结论必须基于输入数据。
3. 对生产环境资源要保守，不能建议直接自动停机。
4. 涉及 GPU、数据库、Redis、生产环境资源时，需要明确人工审批。
5. 报告要有业务价值，不要只复述数据。
6. 使用中文输出。
7. 输出 Markdown 格式。

【云账单摘要】
总成本：{billing_summary.get("total_cost")} 元
平均每日成本：{billing_summary.get("avg_daily_cost")} 元
资源数量：{billing_summary.get("resource_count")}
服务数量：{billing_summary.get("service_count")}
成本最高服务：{billing_summary.get("top_service")}
成本最高服务费用：{billing_summary.get("top_service_cost")} 元

【资源利用率摘要】
资源数量：{utilization_summary.get("resource_count")}
可优化资源数量：{utilization_summary.get("optimization_count")}
闲置资源数量：{utilization_summary.get("idle_count")}
过度配置资源数量：{utilization_summary.get("over_provisioned_count")}
GPU 低利用率资源数量：{utilization_summary.get("gpu_low_count")}
预计月节省金额：{utilization_summary.get("total_estimated_saving")} 元
预计节省比例：{utilization_summary.get("saving_rate")}%

【优化建议明细】
{rec_text}

请按照下面结构输出：

# CloudCostOps 成本优化建议报告

## 1. 总体结论
用 3-5 句话总结当前成本问题、主要优化空间和预计节省价值。

## 2. 关键发现
列出 3-6 条关键发现，每条需要说明证据。

## 3. 优先优化资源
按优先级列出资源、问题、建议动作、预计节省金额和风险等级。

## 4. 风险与人工审批
说明哪些动作不能自动执行，哪些资源必须人工审批。

## 5. 建议执行路线
给出短期、中期、长期执行计划。

## 6. 面向简历项目的技术亮点
总结这个系统体现了哪些 AI Agent 工程能力。
"""
    return prompt


def _fallback_report(
    billing_result: Dict[str, Any],
    utilization_result: Dict[str, Any],
    error_message: str = ""
) -> str:
    billing_summary = billing_result.get("summary", {})
    utilization_summary = utilization_result.get("summary", {})
    recommendations = utilization_result.get("optimization_recommendations", [])

    lines = []
    lines.append("# CloudCostOps 成本优化建议报告")
    lines.append("")
    lines.append("## 1. 总体结论")
    lines.append(
        f"本次账单总成本为 {billing_summary.get('total_cost')} 元，"
        f"资源利用率分析显示共有 {utilization_summary.get('optimization_count')} 个可优化资源。"
    )
    lines.append(
        f"系统预计每月可节省 {utilization_summary.get('total_estimated_saving')} 元，"
        f"节省比例约为 {utilization_summary.get('saving_rate')}%。"
    )
    lines.append("")
    lines.append("## 2. 关键发现")
    lines.append(f"- 成本最高的云服务是 {billing_summary.get('top_service')}，费用为 {billing_summary.get('top_service_cost')} 元。")
    lines.append(f"- 检测到 {utilization_summary.get('idle_count')} 个疑似闲置资源。")
    lines.append(f"- 检测到 {utilization_summary.get('over_provisioned_count')} 个疑似过度配置资源。")
    lines.append(f"- 检测到 {utilization_summary.get('gpu_low_count')} 个 GPU 低利用率资源。")
    lines.append("")
    lines.append("## 3. 优先优化资源")

    if not recommendations:
        lines.append("当前未发现明显可优化资源。")
    else:
        for idx, item in enumerate(recommendations, start=1):
            lines.append(
                f"{idx}. `{item.get('resource_id')}`：问题类型 `{item.get('issue_type')}`，"
                f"建议动作 `{item.get('recommend_action')}`，预计月节省 "
                f"{item.get('estimated_monthly_saving')} 元，风险等级 `{item.get('risk_level')}`。"
            )

    lines.append("")
    lines.append("## 4. 风险与人工审批")
    high_or_medium = [
        x for x in recommendations
        if x.get("need_human_approval")
    ]
    if high_or_medium:
        lines.append("以下资源涉及生产环境、数据库、Redis 或 GPU 等高价值资源，建议进入人工审批流程：")
        for item in high_or_medium:
            lines.append(f"- `{item.get('resource_id')}`，风险等级：{item.get('risk_level')}，原因：{item.get('reason')}")
    else:
        lines.append("当前未发现必须人工审批的高风险优化项。")

    lines.append("")
    lines.append("## 5. 建议执行路线")
    lines.append("- 短期：优先处理测试环境闲置资源和明显低利用率资源。")
    lines.append("- 中期：建立资源利用率巡检机制，形成每周成本治理报告。")
    lines.append("- 长期：接入云厂商 API、Prometheus 指标和审批流，实现自动化 FinOps 工作流。")

    if error_message:
        lines.append("")
        lines.append("## 6. 大模型调用状态")
        lines.append(f"当前使用本地规则生成报告，大模型调用未生效。原因：{error_message}")

    return "\n".join(lines)


def generate_optimization_plan(
    billing_result: Dict[str, Any],
    utilization_result: Dict[str, Any]
) -> Dict[str, Any]:
    start_time = datetime.now()

    recommendations = utilization_result.get("optimization_recommendations", [])
    approval_items = [
        item for item in recommendations
        if item.get("need_human_approval")
    ]

    llm_enabled = has_llm_config()
    llm_error = ""

    if llm_enabled:
        try:
            system_prompt = (
                "你是一个专业的 CloudCostOps / FinOps / AIOps 云成本治理专家，"
                "擅长根据云账单、资源利用率和风险等级生成可执行的成本优化建议。"
            )
            prompt = _build_prompt(billing_result, utilization_result)
            report = call_llm(prompt, system_prompt=system_prompt)
        except Exception as e:
            llm_error = str(e)
            report = _fallback_report(billing_result, utilization_result, error_message=llm_error)
            llm_enabled = False
    else:
        report = _fallback_report(
            billing_result,
            utilization_result,
            error_message="未配置 OPENAI_API_KEY"
        )

    elapsed_time = round((datetime.now() - start_time).total_seconds(), 3)

    return {
        "success": True,
        "llm_enabled": llm_enabled,
        "llm_model": OPENAI_MODEL if llm_enabled else "local-rule-fallback",
        "llm_error": llm_error,
        "markdown_report": report,
        "approval_items": approval_items,
        "approval_count": len(approval_items),
        "estimated_monthly_saving": utilization_result.get("summary", {}).get("total_estimated_saving", 0),
        "saving_rate": utilization_result.get("summary", {}).get("saving_rate", 0),
        "elapsed_time": elapsed_time
    }