import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="CloudCostOps Agent",
    page_icon="☁️",
    layout="wide"
)

st.title("CloudCostOps Agent 云成本优化与资源治理平台")
st.caption("Cloud Cost Optimization Agent powered by FastAPI + Streamlit + Pandas")

with st.sidebar:
    st.header("数据上传")
    st.write("上传云账单 CSV 文件")

    uploaded_file = st.file_uploader(
        "选择 CSV 文件",
        type=["csv"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("### v0.1 功能")
    st.write("账单上传")
    st.write("成本统计")
    st.write("服务成本分析")
    st.write("异常成本资源识别")

st.subheader("云账单成本分析")

if uploaded_file is not None:
    st.info(f"已选择文件：{uploaded_file.name}")

    if st.button("开始分析账单", use_container_width=True):
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type
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

                st.markdown("### Agent 初步分析")
                st.write(result.get("analysis_comment", ""))

                st.markdown("### 每日成本趋势")
                daily_df = pd.DataFrame(result["daily_cost"])
                if not daily_df.empty:
                    fig = px.line(
                        daily_df,
                        x="date",
                        y="cost",
                        markers=True,
                        title="Daily Cloud Cost Trend"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("### 各云服务成本占比")
                service_df = pd.DataFrame(result["service_cost"])
                if not service_df.empty:
                    fig = px.bar(
                        service_df,
                        x="service",
                        y="cost",
                        title="Cost by Cloud Service"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(service_df, use_container_width=True)

                st.markdown("### 环境成本分布")
                env_df = pd.DataFrame(result["env_cost"])
                if not env_df.empty:
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
            st.code("python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level debug")
        except Exception as e:
            st.error("请求过程中出现异常")
            st.write(str(e))
else:
    st.info("请先在左侧上传云账单 CSV 文件。")