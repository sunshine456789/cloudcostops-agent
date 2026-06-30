# CloudCostOps Agent

CloudCostOps Agent 是一个面向互联网企业云成本优化与资源治理场景的 AI Agent 平台，支持云账单成本分析、资源利用率分析、AI 降本建议生成、Agent 执行轨迹可视化、人工审批记录与审计日志追踪。

本项目模拟企业内部 FinOps / AIOps / CloudOps 工作流，帮助研发、运维和平台团队从云账单与资源监控数据中发现高成本、低利用率、闲置和过度配置资源，并通过大模型生成可执行的成本优化建议。

---

## 1. Project Overview

在互联网企业中，云资源成本通常来源于 ECS、GPU、RDS、Redis、OSS 等多类服务。如果缺少持续治理机制，容易出现以下问题：

- 测试环境资源长期运行但无人使用
- GPU 训练资源低利用率运行，造成高额浪费
- 生产环境 Redis / RDS 规格过高但未及时降配
- 对象存储、日志存储长期堆积
- 成本数据与资源利用率数据割裂，难以定位优化优先级
- 高风险资源缺少审批流程，自动优化存在业务风险

CloudCostOps Agent 通过“成本分析 + 利用率分析 + AI 建议生成 + 风险控制 + 人工审批 + 审计日志”的方式，构建了一个端到端的云成本治理 Demo 系统。

---

## 2. Core Features

### v0.1 Cloud Billing Analysis

支持上传云账单 CSV 文件，并自动完成：

- 云账单 CSV 上传
- 总成本统计
- 平均每日成本统计
- 服务维度成本分析
- 环境维度成本分析
- 每日成本趋势分析
- Top 成本资源识别
- 疑似成本异常资源识别

---

### v0.2 Resource Utilization Analysis

支持上传资源利用率 CSV 文件，并自动分析：

- CPU 平均利用率
- 内存平均利用率
- 磁盘平均利用率
- GPU 平均利用率
- 闲置资源识别
- 过度配置资源识别
- GPU 低利用率资源识别
- 预计月节省金额计算
- 节省比例计算
- 优化建议资源列表生成

---

### v0.3 AI Cost Optimization Agent

接入 DeepSeek 大模型，通过 OpenAI-Compatible API 生成自然语言降本优化报告。

支持：

- 云账单数据与资源利用率数据联合分析
- AI 生成 Markdown 成本优化报告
- 识别重点优化资源
- 输出风险等级
- 输出预计节省金额
- 输出短期、中期、长期优化路线
- 输出面向简历项目的技术亮点

如果未配置 API Key，系统会自动回退到本地规则报告生成模式，保证基础功能可运行。

---

### v0.4 Agent Workflow Trace

新增 Agent 执行轨迹可视化，用于展示完整多 Agent 工作流：

- Billing Analysis Agent
- Resource Utilization Agent
- Cost Anomaly Agent
- Optimization Planning Agent
- Risk Control Agent
- Human Approval Agent
- Report Agent

页面会展示：

- 总步骤数
- 成功步骤数
- 需关注步骤数
- 待审批步骤数
- 模拟执行耗时
- 每个 Agent 的输入、动作、输出、证据和状态
- Mermaid 工作流结构代码

---

### v0.5 Approval Audit Log and Report Export

新增企业场景中的审批与审计能力：

- Markdown 成本优化报告导出
- 后端自动保存报告文件
- 人工审批决策记录
- JSONL 审计日志写入
- Agent Run 运行日志记录
- Approval ID 自动生成
- Run ID 自动生成

运行后会生成：

```text
logs/agent_runs.jsonl
logs/approval_decisions.jsonl
outputs/reports/*.md