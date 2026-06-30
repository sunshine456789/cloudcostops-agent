# CloudCostOps Agent

CloudCostOps Agent 是一个面向互联网企业云成本优化与资源治理场景的 AI Agent 平台。

当前 v0.1 版本支持：

- 云账单 CSV 上传
- 总成本统计
- 每日成本趋势分析
- 云服务成本占比分析
- 环境成本分布分析
- Top 成本资源识别
- 疑似成本异常资源识别

## Tech Stack

- Python 3.10
- FastAPI
- Streamlit
- Pandas
- Plotly
- scikit-learn
- OpenAI-compatible API

## Run Backend

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level debug

## Run Frontend

streamlit run frontend/app.py

## Example Data

Use:

examples/cloud_billing_sample.csv