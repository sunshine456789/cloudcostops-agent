# CloudCostOps Pro

> AI-driven FinOps multi-agent platform for cloud cost analysis, resource optimization and human-in-the-loop risk control.

CloudCostOps Pro 是一个面向云资源成本治理场景的 AI FinOps 多智能体平台。

项目基于 **FastAPI + LangGraph + DeepSeek + SQLAlchemy + React + TypeScript** 构建，将云账单分析、资源利用率诊断、风险评估、优化方案生成以及人工审批组织为完整的 Agent Workflow。

系统能够从云成本与资源利用率数据中识别闲置、低利用率和过度配置资源，并生成降配、释放等成本优化建议。对于涉及生产环境或高风险资源的操作，工作流不会直接执行，而是进入 **Human-in-the-loop 人工审批节点**，由用户决定批准或拒绝后再继续执行。

---

## 1. Project Overview

在企业云环境中，ECS、GPU、Redis、OSS、数据库等资源通常会长期积累，容易出现：

- 闲置资源持续产生费用
- GPU 等高成本资源利用率过低
- Redis / 数据库实例规格过高
- 测试环境资源长期运行
- OSS / 日志存储长期堆积
- 自动优化可能影响生产环境稳定性

CloudCostOps Pro 将传统 FinOps 分析流程拆分为多个 Agent，由 LangGraph 负责工作流编排，并通过 DeepSeek 生成优化决策。

整体流程：

```text
Cloud Billing Data
        │
        ▼
Data Validation Agent
        │
        ▼
Billing Analysis Agent
        │
        ▼
Resource Utilization Agent
        │
        ▼
Risk Control Agent
        │
        ▼
Optimization Planning Agent
        │
        ├──────── Low Risk ────────► Workflow Completion
        │
        └──────── High Risk
                     │
                     ▼
             Human Approval Agent
                │           │
             Approve      Reject
                │           │
                ▼           ▼
         Continue Flow   Stop Action
```

---

## 2. Core Features

### Multi-Agent FinOps Workflow

基于 **LangGraph** 构建状态驱动的多 Agent 工作流，将复杂成本优化任务拆分为多个职责明确的节点：

| Agent | Responsibility |
|---|---|
| Data Validation Agent | 校验账单与资源利用率数据 |
| Billing Analysis Agent | 分析总体成本、服务成本及异常资源 |
| Resource Utilization Agent | 分析 CPU、Memory、Disk、GPU 利用率 |
| Risk Control Agent | 判断优化动作的业务风险 |
| Optimization Planning Agent | 调用 LLM 生成优化建议 |
| Human Approval Agent | 处理高风险操作人工审批 |
| Workflow Completion Agent | 完成工作流并记录执行结果 |

---

### AI Cost Optimization

系统结合账单数据和资源利用率数据识别潜在优化对象，例如：

```text
Low CPU Utilization
Low Memory Utilization
Idle GPU Resource
Oversized Redis Instance
Unused OSS Resource
Over-Provisioned Infrastructure
```

并生成对应优化动作：

```text
stop_or_release
downsize_instance
release_idle_resource
resource_rightsizing
```

同时计算：

- 当前资源成本
- 预计节省金额
- 预计节省率
- 风险等级
- 推荐操作
- 优化原因

---

### DeepSeek Optimization Planning

Optimization Planning Agent 接入 **DeepSeek LLM**。

LLM 并不是直接处理原始云资源，而是在前置 Agent 完成：

```text
Data Validation
      ↓
Billing Analysis
      ↓
Utilization Analysis
      ↓
Risk Assessment
```

之后，根据结构化分析结果生成最终优化方案。

这种设计将：

```text
Deterministic Analysis
+
LLM Reasoning
```

结合起来，降低完全依赖大模型直接判断所带来的不稳定性。

---

### Human-in-the-loop Risk Control

CloudCostOps Pro 不允许 Agent 无条件执行高风险操作。

Risk Control Agent 会检查：

- Production Environment
- Database Resource
- Redis Resource
- GPU Resource
- Stop / Release Action
- High-risk Optimization

当检测到高风险操作后：

```text
Optimization Planning Agent
        │
        ▼
Human Approval Agent
        │
   ┌────┴────┐
   │         │
Approve    Reject
   │         │
   ▼         ▼
Continue   Stop
```

用户可以在前端 **人工审批中心** 中查看完整任务信息并选择：

```text
批准优化方案
拒绝优化方案
```

审批结果随后写回 Agent Workflow。

---

## 3. Agent Run Tracking

每一次 CloudCostOps 工作流都会生成独立的：

```text
run_id
```

例如：

```text
run_20260812211954_ebd7372b
```

系统会持久化记录：

- Agent Run
- Workflow Steps
- Optimization Items
- Risk Level
- Approval Decision
- Estimated Saving
- Run Status
- Generated Report

前端可以查看每一次 Agent Workflow 的完整执行轨迹。

---

## 4. Workflow Observability

Agent Run Detail 页面可以查看每个 Agent Node 的执行情况，包括：

```text
Step Name
Agent Name
Execution Status
Execution Result
Duration
Key Output
```

例如：

```text
01 Data Validation Agent
02 Billing Analysis Agent
03 Resource Utilization Agent
04 Risk Control Agent
05 Optimization Planning Agent
06 Human Approval Agent
07 Workflow Completion Agent
```

从而避免多 Agent 系统成为不可观察的“黑盒”。

---

## 5. Cloud FinOps Dashboard

React 前端提供完整的 Cloud FinOps 控制台，目前主要包括：

```text
Overview
Cost Optimization
Agent Runs
Human Approval
Resource Center
Optimization Reports
```

### Overview

展示：

- Agent Runs
- Estimated Monthly Saving
- Average Saving Rate
- Pending Approvals

### Cost Optimization

上传：

```text
Cloud Billing CSV
Resource Utilization CSV
```

然后启动：

```text
CloudCostOps AI Optimization Workflow
```

系统自动执行完整 Agent 工作流。

### Agent Runs

展示所有历史运行任务，包括：

- Run ID
- Estimated Saving
- Risk Level
- Run Status

### Human Approval

集中处理 Risk Control Agent 标记的高风险任务。

### Resource Center

查看被 Agent 分析的云资源以及对应运行指标。

### Optimization Reports

查看系统生成的成本优化结果和报告。

---

## 6. System Architecture

```text
                     ┌───────────────────────┐
                     │     React Frontend    │
                     │      TypeScript       │
                     └───────────┬───────────┘
                                 │
                              REST API
                                 │
                     ┌───────────▼───────────┐
                     │        FastAPI        │
                     │     API / Service     │
                     └───────────┬───────────┘
                                 │
               ┌─────────────────┴─────────────────┐
               │                                   │
        ┌──────▼──────┐                    ┌───────▼────────┐
        │  LangGraph  │                    │   SQLAlchemy   │
        │ Agent Graph │                    │ Persistence    │
        └──────┬──────┘                    └───────┬────────┘
               │                                   │
     ┌─────────┼─────────┐                         │
     │         │         │                         ▼
     ▼         ▼         ▼                       SQLite
 Billing   Resource    Risk
 Agent      Agent      Agent
     │         │         │
     └─────────┼─────────┘
               ▼
      Optimization Agent
               │
               ▼
           DeepSeek
               │
               ▼
       Human Approval
```

---

## 7. Tech Stack

### Backend

- Python
- FastAPI
- LangGraph
- DeepSeek API
- SQLAlchemy
- Alembic
- SQLite
- Pandas
- Pydantic

### Frontend

- React
- TypeScript
- Vite
- CSS
- REST API

### Agent / AI

- Multi-Agent Workflow
- State-based Agent Orchestration
- LLM Reasoning
- Human-in-the-loop
- Risk-aware Decision Making
- Workflow Persistence

### Engineering

- Git
- GitHub
- Feature Branch Workflow
- Pull Request
- Alembic Database Migration
- Windows Batch Launcher

---

## 8. Project Structure

```text
cloudcostops-agent/
│
├── backend/
│   └── app/
│       │
│       ├── agents/
│       │   └── cloud_cost/
│       │       ├── graph.py
│       │       ├── nodes.py
│       │       └── state.py
│       │
│       ├── api/
│       │   └── routes/
│       │       ├── agent.py
│       │       ├── analysis.py
│       │       ├── health.py
│       │       └── runs.py
│       │
│       ├── db/
│       │   └── models/
│       │       ├── agent_run.py
│       │       ├── workflow_step.py
│       │       ├── optimization_item.py
│       │       ├── approval_decision.py
│       │       └── generated_report.py
│       │
│       ├── repositories/
│       │
│       ├── schemas/
│       │
│       └── services/
│           ├── run_persistence_service.py
│           ├── run_query_service.py
│           └── upload_service.py
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── cloudcost.ts
│   │   ├── pages/
│   │   │   └── CostOptimization.tsx
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   └── package.json
│
├── alembic/
│   └── versions/
│
├── examples/
│
├── requirements.txt
├── run_backend.bat
├── run_frontend.bat
└── start_cloudcostops.bat
```

---

## 9. Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/sunshine456789/cloudcostops-agent.git
cd cloudcostops-agent
```

---

### 2. Create Python Environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

---

### 3. Configure Environment

Copy:

```text
.env.example
```

to:

```text
.env
```

and configure your DeepSeek API credential.

> Do not commit `.env` or API keys to GitHub.

---

### 4. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

### 5. One-click Startup

Windows users can directly run:

```text
start_cloudcostops.bat
```

The launcher starts both backend and frontend.

Default local services:

```text
Frontend:
http://127.0.0.1:5173

FastAPI:
http://127.0.0.1:8000

Swagger:
http://127.0.0.1:8000/docs
```

You can also start them separately:

```text
run_backend.bat
run_frontend.bat
```

---

## 10. Typical Workflow

### Step 1

Upload cloud billing data.

### Step 2

Upload resource utilization data.

### Step 3

Start AI Cost Optimization.

### Step 4

LangGraph automatically executes:

```text
Validation
→ Billing Analysis
→ Utilization Analysis
→ Risk Control
→ Optimization Planning
```

### Step 5

If the optimization is low risk:

```text
Workflow → Complete
```

If the optimization is high risk:

```text
Workflow → Human Approval
```

### Step 6

User approves or rejects the optimization.

### Step 7

The final workflow status, approval result and optimization report are persisted.

---

## 11. Design Highlights

### Why LangGraph?

Cloud cost optimization is not a single LLM prompt task.

It contains multiple stages with different responsibilities:

```text
Data Processing
Analysis
Risk Control
LLM Planning
Human Decision
Workflow Resume
```

LangGraph makes these stages explicit and allows the system to maintain workflow state between different Agent Nodes.

---

### Why Human-in-the-loop?

An LLM-generated optimization recommendation may involve:

```text
Stop Production Resource
Release Cloud Storage
Downsize Database
Downsize Redis
Release GPU
```

These operations may create business risk.

Therefore, CloudCostOps Pro separates:

```text
AI Recommendation
```

from:

```text
Actual Decision
```

High-risk optimization must receive human confirmation before the workflow continues.

---

### Why Persistence?

Agent systems need more than a final answer.

For production-style applications we also need to know:

```text
What happened?
Which Agent executed?
What result was produced?
Why did the workflow stop?
Who approved the operation?
What optimization was recommended?
```

Therefore CloudCostOps Pro persists Agent Run and Workflow Step information through SQLAlchemy.

---

## 12. Current Status

Current version has completed:

- [x] FastAPI backend
- [x] React + TypeScript frontend
- [x] Cloud billing analysis
- [x] Resource utilization analysis
- [x] LangGraph multi-agent workflow
- [x] DeepSeek optimization planning
- [x] Risk control agent
- [x] Human approval workflow
- [x] Approve / Reject branches
- [x] Agent Run persistence
- [x] Workflow Step tracking
- [x] Optimization Item persistence
- [x] Approval Decision persistence
- [x] Agent Runs dashboard
- [x] Human Approval Center
- [x] Resource Center
- [x] Optimization Reports
- [x] FastAPI Swagger API
- [x] Windows one-click launcher
- [x] End-to-end workflow testing

---

## 13. Future Work

Future versions can further introduce:

- AWS / Alibaba Cloud / Azure billing API integration
- Real-time cloud monitoring metrics
- Scheduled FinOps analysis
- Multi-cloud resource management
- Redis / RDS / ECS automatic rightsizing
- Kubernetes cost optimization
- Approval roles and RBAC
- Agent evaluation
- LLM output validation
- Docker deployment
- CI/CD
- PostgreSQL production database
- Redis task state management
- WebSocket real-time workflow updates

---

## 14. What I Learned

This project focuses not only on calling an LLM API, but also on how to build a complete AI application around the model:

```text
LLM
+
Agent Workflow
+
Backend Service
+
Database
+
Risk Control
+
Human Approval
+
Frontend Visualization
+
Engineering Workflow
```

The core challenge is turning AI-generated suggestions into a controllable, observable and auditable application workflow.

---

## License

This project is currently used for learning, portfolio demonstration and AI Agent engineering practice.