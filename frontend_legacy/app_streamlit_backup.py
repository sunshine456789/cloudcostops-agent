import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="CloudCostOps Agent",
    page_icon="☁️",
    layout="wide"
)

st.title("CloudCostOps Agent 云成本优化与资源治理平台")
st.caption("Cloud Cost Optimization Agent powered by FastAPI + Streamlit + Pandas + DeepSeek")

if "ai_result" not in st.session_state:
    st.session_state["ai_result"] = None

with st.sidebar:
    st.header("数据上传")
    st.write("支持云账单 CSV 和资源利用率 CSV")

    st.markdown("---")
    st.markdown("### 当前版本")
    st.write("v0.1：云账单成本分析")
    st.write("v0.2：资源利用率分析")
    st.write("v0.3：DeepSeek 降本建议 Agent")
    st.write("v0.4：Agent 执行轨迹可视化")
    st.write("v0.5：审批记录 + 审计日志 + 报告导出")


def render_workflow_trace(result):
    st.markdown("### Agent 执行轨迹")

    workflow_steps = result.get("workflow_steps", [])
    workflow_summary = result.get("workflow_summary", {})

    if not workflow_steps:
        st.info("当前结果中没有工作流轨迹。")
        return

    total_steps = workflow_summary.get("total_steps", len(workflow_steps))
    success_count = workflow_summary.get("success_count", 0)
    warning_count = workflow_summary.get("warning_count", 0)
    pending_count = workflow_summary.get("pending_count", 0)
    error_count = workflow_summary.get("error_count", 0)
    total_duration_ms = workflow_summary.get("total_duration_ms", 0)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("总步骤", total_steps)
    col2.metric("成功", success_count)
    col3.metric("需关注", warning_count)
    col4.metric("待审批", pending_count)
    col5.metric("模拟耗时", f"{total_duration_ms} ms")

    progress_value = 0
    if total_steps > 0:
        finished_count = success_count + warning_count + pending_count
        progress_value = min(finished_count / total_steps, 1.0)

    st.progress(progress_value)

    trace_df = pd.DataFrame(workflow_steps)

    display_columns = [
        "step_id",
        "agent_name",
        "stage",
        "status_label",
        "duration_ms",
        "key_output"
    ]

    existing_columns = [col for col in display_columns if col in trace_df.columns]
    st.dataframe(trace_df[existing_columns], use_container_width=True)

    st.markdown("### 工作流细节")

    for step in workflow_steps:
        title = f"{step.get('step_id')}. {step.get('agent_name')} - {step.get('status_label')}"
        with st.expander(title):
            st.write(f"**阶段：** {step.get('stage')}")
            st.write(f"**输入：** {step.get('input')}")
            st.write(f"**执行动作：** {step.get('action')}")
            st.write(f"**关键输出：** {step.get('key_output')}")
            st.write(f"**耗时：** {step.get('duration_ms')} ms")

            evidence = step.get("evidence", [])
            if evidence:
                st.write("**证据：**")
                for item in evidence:
                    st.write(f"- {item}")

    workflow_mermaid = result.get("workflow_mermaid")
    if workflow_mermaid:
        st.markdown("### 工作流结构")
        st.code(workflow_mermaid, language="mermaid")


def render_approval_section(result):
    st.markdown("### 审批决策记录")

    run_id = result.get("run_id", "")
    st.write(f"当前 Run ID：`{run_id}`")

    with st.form("approval_form"):
        approval_decision = st.selectbox(
            "请选择审批决策：",
            [
                "仅记录建议，不执行任何动作",
                "批准低风险优化项",
                "中高风险全部转人工审批",
                "拒绝本次全部优化建议"
            ]
        )

        operator = st.text_input(
            "审批人 / 操作人：",
            value="demo_user"
        )

        approval_comment = st.text_area(
            "审批备注：",
            value="测试环境资源可优先释放，生产环境资源需要业务负责人确认。"
        )

        approved_scope = st.selectbox(
            "审批范围：",
            [
                "low_risk_only",
                "manual_review_required",
                "reject_all",
                "record_only"
            ]
        )

        submitted = st.form_submit_button(
            "提交审批决策并写入审计日志",
            use_container_width=True
        )

    if submitted:
        payload = {
            "run_id": run_id,
            "decision": approval_decision,
            "operator": operator,
            "comment": approval_comment,
            "approved_scope": approved_scope
        }

        try:
            approval_response = requests.post(
                f"{API_URL}/agent/approval-decision",
                json=payload,
                timeout=60
            )

            approval_result = approval_response.json()

            if approval_result.get("success"):
                st.success(
                    f"审批决策记录成功，Approval ID：{approval_result.get('approval_id')}"
                )
            else:
                st.error("审批决策记录失败")
                st.write(approval_result)

        except requests.exceptions.ConnectionError:
            st.error("无法连接后端服务，请确认 FastAPI 后端正在运行。")
        except Exception as e:
            st.error("提交审批决策时出现异常")
            st.write(str(e))


def render_report_export(result):
    st.markdown("### 报告导出")

    report_text = result.get("markdown_report", "")
    report_filename = result.get("report_filename", "cloudcostops_report.md")

    st.write(f"报告 ID：`{result.get('report_id')}`")
    st.write(f"后端保存状态：`{result.get('report_saved')}`")

    st.download_button(
        label="下载 Markdown 成本优化报告",
        data=report_text.encode("utf-8"),
        file_name=report_filename,
        mime="text/markdown",
        use_container_width=True
    )


def render_ai_result(result):
    if not result:
        return

    if not result.get("success"):
        st.error("AI 降本建议生成失败")
        st.write(result)
        return

    st.success("AI 降本建议生成完成")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("预计月节省", f"{result.get('estimated_monthly_saving')} 元")
    col2.metric("节省比例", f"{result.get('saving_rate')}%")
    col3.metric("人工审批项", result.get("approval_count"))
    col4.metric("模型", result.get("llm_model"))

    if result.get("llm_enabled"):
        st.success("DeepSeek 大模型调用成功")
    else:
        st.warning("当前使用本地规则兜底报告。请检查 .env 中的 OPENAI_API_KEY 或 DeepSeek 配置。")
        if result.get("llm_error"):
            st.code(result.get("llm_error"))

    render_workflow_trace(result)

    st.markdown("### Optimization Planning Agent 报告")
    st.markdown(result.get("markdown_report", ""))

    render_report_export(result)

    approval_items = result.get("approval_items", [])
    st.markdown("### 需要人工审批的资源")

    if not approval_items:
        st.info("当前没有必须人工审批的资源。")
    else:
        approval_df = pd.DataFrame(approval_items)
        st.dataframe(approval_df, use_container_width=True)

    render_approval_section(result)

    st.markdown("### 执行信息")
    st.write(f"Run ID：`{result.get('run_id')}`")
    st.write(f"账单文件：{result.get('billing_filename')}")
    st.write(f"利用率文件：{result.get('utilization_filename')}")
    st.write(f"总响应耗时：{result.get('total_elapsed_time')} 秒")


tab1, tab2, tab3 = st.tabs([
    "云账单成本分析",
    "资源利用率分析",
    "AI 降本建议 Agent"
])


with tab1:
    st.subheader("云账单成本分析")

    billing_file = st.file_uploader(
        "上传云账单 CSV 文件",
        type=["csv"],
        key="billing_file"
    )

    if billing_file is not None:
        st.info(f"已选择文件：{billing_file.name}")

        if st.button("开始分析账单", use_container_width=True):
            files = {
                "file": (
                    billing_file.name,
                    billing_file.getvalue(),
                    billing_file.type
                )
            }

            try:
                with st.spinner("CloudCostOps Agent 正在分析云成本数据..."):
                    response = requests.post(
                        f"{API_URL}/analyze/billing",
                        files=files,
                        timeout=120
                    )

                result = response.json()

                if not result.get("success"):
                    st.error("分析失败")
                    st.write(result)
                else:
                    st.success("账单分析完成")

                    summary = result["summary"]

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("总成本", f"{summary['total_cost']} 元")
                    col2.metric("平均每日成本", f"{summary['avg_daily_cost']} 元")
                    col3.metric("资源数量", summary["resource_count"])
                    col4.metric("服务数量", summary["service_count"])

                    st.markdown("### Billing Analysis Agent 初步分析")
                    st.write(result.get("analysis_comment", ""))

                    daily_df = pd.DataFrame(result["daily_cost"])
                    if not daily_df.empty:
                        st.markdown("### 每日成本趋势")
                        fig = px.line(
                            daily_df,
                            x="date",
                            y="cost",
                            markers=True,
                            title="Daily Cloud Cost Trend"
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    service_df = pd.DataFrame(result["service_cost"])
                    if not service_df.empty:
                        st.markdown("### 各云服务成本占比")
                        fig = px.bar(
                            service_df,
                            x="service",
                            y="cost",
                            title="Cost by Cloud Service"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        st.dataframe(service_df, use_container_width=True)

                    env_df = pd.DataFrame(result["env_cost"])
                    if not env_df.empty:
                        st.markdown("### 环境成本分布")
                        fig = px.pie(
                            env_df,
                            names="env",
                            values="cost",
                            title="Cost by Environment"
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    st.markdown("### Top 成本资源")
                    top_df = pd.DataFrame(result["top_resources"])
                    st.dataframe(top_df, use_container_width=True)

                    st.markdown("### 疑似成本异常资源")
                    anomaly_df = pd.DataFrame(result["anomaly_resources"])

                    if anomaly_df.empty:
                        st.info("当前未检测到明显成本异常资源。")
                    else:
                        st.warning("检测到疑似成本异常资源，建议重点排查。")
                        st.dataframe(anomaly_df, use_container_width=True)

                    st.markdown("### 执行信息")
                    st.write(f"文件名：{result.get('filename')}")
                    st.write(f"响应耗时：{result.get('elapsed_time')} 秒")

            except requests.exceptions.ConnectionError:
                st.error("无法连接后端服务，请先启动 FastAPI 后端。")
                st.code(
                    "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level debug"
                )
            except Exception as e:
                st.error("请求过程中出现异常")
                st.write(str(e))
    else:
        st.info("请上传云账单 CSV 文件。")


with tab2:
    st.subheader("资源利用率分析")

    utilization_file = st.file_uploader(
        "上传资源利用率 CSV 文件",
        type=["csv"],
        key="utilization_file"
    )

    if utilization_file is not None:
        st.info(f"已选择文件：{utilization_file.name}")

        if st.button("开始分析资源利用率", use_container_width=True):
            files = {
                "file": (
                    utilization_file.name,
                    utilization_file.getvalue(),
                    utilization_file.type
                )
            }

            try:
                with st.spinner("Resource Utilization Agent 正在分析资源利用率..."):
                    response = requests.post(
                        f"{API_URL}/analyze/utilization",
                        files=files,
                        timeout=120
                    )

                result = response.json()

                if not result.get("success"):
                    st.error("分析失败")
                    st.write(result)
                else:
                    st.success("资源利用率分析完成")

                    summary = result["summary"]

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("资源数量", summary["resource_count"])
                    col2.metric("可优化资源", summary["optimization_count"])
                    col3.metric("预计月节省", f"{summary['total_estimated_saving']} 元")
                    col4.metric("节省比例", f"{summary['saving_rate']}%")

                    col5, col6, col7 = st.columns(3)
                    col5.metric("闲置资源", summary["idle_count"])
                    col6.metric("过度配置资源", summary["over_provisioned_count"])
                    col7.metric("GPU 低利用率", summary["gpu_low_count"])

                    st.markdown("### Resource Utilization Agent 分析")
                    st.write(result.get("analysis_comment", ""))

                    service_df = pd.DataFrame(result["service_utilization"])
                    if not service_df.empty:
                        st.markdown("### 各服务平均利用率")
                        fig = px.bar(
                            service_df,
                            x="service",
                            y=[
                                "avg_cpu_utilization",
                                "avg_memory_utilization",
                                "avg_gpu_utilization"
                            ],
                            barmode="group",
                            title="Average Utilization by Cloud Service"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        st.dataframe(service_df, use_container_width=True)

                    env_df = pd.DataFrame(result["env_utilization"])
                    if not env_df.empty:
                        st.markdown("### 各环境资源利用率")
                        fig = px.bar(
                            env_df,
                            x="env",
                            y="monthly_cost",
                            title="Monthly Cost by Environment"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        st.dataframe(env_df, use_container_width=True)

                    st.markdown("### 资源利用率画像")
                    resource_df = pd.DataFrame(result["resource_profile"])
                    st.dataframe(resource_df, use_container_width=True)

                    st.markdown("### 优化建议资源列表")
                    rec_df = pd.DataFrame(result["optimization_recommendations"])

                    if rec_df.empty:
                        st.info("当前未发现明显可优化资源。")
                    else:
                        st.warning("检测到可优化资源，建议进入人工审批流程。")
                        st.dataframe(rec_df, use_container_width=True)

                        high_risk = rec_df[rec_df["risk_level"] == "high"]
                        if not high_risk.empty:
                            st.error("存在生产环境或高风险资源，禁止自动执行优化，必须人工审批。")

                        st.markdown("### Human Approval 模拟审批")
                        selected_action = st.radio(
                            "请选择处理动作：",
                            ["仅生成建议，不执行", "批准低风险建议", "全部转人工审批"]
                        )

                        if st.button("保存审批决策"):
                            st.success(f"审批决策已记录：{selected_action}")

                    st.markdown("### 执行信息")
                    st.write(f"文件名：{result.get('filename')}")
                    st.write(f"响应耗时：{result.get('elapsed_time')} 秒")

            except requests.exceptions.ConnectionError:
                st.error("无法连接后端服务，请先启动 FastAPI 后端。")
                st.code(
                    "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level debug"
                )
            except Exception as e:
                st.error("请求过程中出现异常")
                st.write(str(e))
    else:
        st.info("请上传资源利用率 CSV 文件。")


with tab3:
    st.subheader("AI 降本建议 Agent")

    st.write(
        "同时上传云账单 CSV 和资源利用率 CSV，系统会联合分析成本、利用率、风险等级，"
        "生成 Markdown 降本优化报告，并支持审批决策记录与审计日志。"
    )

    col_a, col_b = st.columns(2)

    with col_a:
        ai_billing_file = st.file_uploader(
            "上传云账单 CSV",
            type=["csv"],
            key="ai_billing_file"
        )

    with col_b:
        ai_utilization_file = st.file_uploader(
            "上传资源利用率 CSV",
            type=["csv"],
            key="ai_utilization_file"
        )

    if ai_billing_file is not None:
        st.info(f"已选择账单文件：{ai_billing_file.name}")

    if ai_utilization_file is not None:
        st.info(f"已选择利用率文件：{ai_utilization_file.name}")

    if ai_billing_file is not None and ai_utilization_file is not None:
        if st.button("生成 AI 降本优化建议", use_container_width=True):
            files = {
                "billing_file": (
                    ai_billing_file.name,
                    ai_billing_file.getvalue(),
                    ai_billing_file.type
                ),
                "utilization_file": (
                    ai_utilization_file.name,
                    ai_utilization_file.getvalue(),
                    ai_utilization_file.type
                )
            }

            try:
                with st.spinner("Optimization Planning Agent 正在生成降本优化建议..."):
                    response = requests.post(
                        f"{API_URL}/agent/optimization-plan",
                        files=files,
                        timeout=180
                    )

                result = response.json()
                st.session_state["ai_result"] = result

            except requests.exceptions.ConnectionError:
                st.error("无法连接后端服务，请先启动 FastAPI 后端。")
                st.code(
                    "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level debug"
                )
            except Exception as e:
                st.error("请求过程中出现异常")
                st.write(str(e))
    else:
        st.info("请同时上传云账单 CSV 和资源利用率 CSV。")

    if st.session_state.get("ai_result") is not None:
        render_ai_result(st.session_state["ai_result"])

        if st.button("清空当前 AI 分析结果", use_container_width=True):
            st.session_state["ai_result"] = None
            st.rerun()