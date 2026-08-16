import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bot,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  CloudCog,
  FileChartColumn,
  Gauge,
  LayoutDashboard,
  RefreshCw,
  ServerCog,
  ShieldCheck,
  Sparkles,
  Timer,
} from "lucide-react";
import {
  getRunDetail,
  listRuns,
} from "./api/cloudcost";
import type {
  AgentRun,
  RunDetail,
} from "./api/cloudcost";
import CostOptimization from "./pages/CostOptimization";
import "./App.css";

type ActivePage =
  | "overview"
  | "optimization"
  | "runs"
  | "approval"
  | "resources"
  | "reports";

type ResourceRow = {
  run_id: string;
  resource_id: string;
  service: string;
  env: string;
  owner: string;
  region: string;
  avg_cpu_utilization: number;
  avg_memory_utilization: number;
  avg_disk_utilization: number;
  avg_gpu_utilization: number;
  monthly_cost: number;
  issue_type: string;
  recommend_action: string;
  estimated_monthly_saving: number;
  risk_level: string;
  need_human_approval: boolean;
  reason: string;
};

type ReportRow = {
  run_id: string;
  report_id: string;
  report_filename: string;
  report_path: string;
  report_saved: boolean;
  created_at: string;
};

function formatMoney(value?: number | null) {
  if (value === null || value === undefined) {
    return "¥0";
  }

  return `¥${Number(value).toLocaleString("zh-CN", {
    maximumFractionDigits: 2,
  })}`;
}

function formatTime(value?: string | null) {
  if (!value) {
    return "--";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-CN");
}

function formatPercent(value?: number | null) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function StatusBadge({
  status,
}: {
  status?: string | null;
}) {
  const text = status || "unknown";

  const className =
    text === "completed"
      ? "badge badge-success"
      : text === "pending_approval"
        ? "badge badge-warning"
        : text === "failed" ||
            text === "rejected"
          ? "badge badge-danger"
          : "badge badge-neutral";

  const labels: Record<string, string> = {
    completed: "已完成",
    pending_approval: "待审批",
    failed: "失败",
    rejected: "已拒绝",
    running: "运行中",
  };

  return (
    <span className={className}>
      {labels[text] || text}
    </span>
  );
}

function RiskBadge({
  risk,
}: {
  risk?: string | null;
}) {
  if (!risk) {
    return (
      <span className="risk risk-none">
        --
      </span>
    );
  }

  return (
    <span
      className={`risk risk-${risk.toLowerCase()}`}
    >
      {risk.toUpperCase()}
    </span>
  );
}

function App() {
  const [activePage, setActivePage] =
    useState<ActivePage>("overview");

  const [runs, setRuns] =
    useState<AgentRun[]>([]);

  const [selectedRun, setSelectedRun] =
    useState<RunDetail | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [detailLoading, setDetailLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [resourceRows, setResourceRows] =
    useState<ResourceRow[]>([]);

  const [resourceLoading, setResourceLoading] =
    useState(false);

  const [reportRows, setReportRows] =
    useState<ReportRow[]>([]);

  const [reportLoading, setReportLoading] =
    useState(false);

  const [approvalBusy, setApprovalBusy] =
    useState<string | null>(null);

  const [approvalMessage, setApprovalMessage] =
    useState("");

  async function fetchFreshRuns(): Promise<AgentRun[]> {
    const result = await listRuns({
      page: 1,
      page_size: 100,
    });

    const items = result.items || [];

    setRuns(items);

    return items;
  }

  async function loadRuns() {
    try {
      setLoading(true);
      setError("");

      await fetchFreshRuns();
    } catch (err) {
      console.error(err);

      setError(
        "无法连接 CloudCostOps 后端，请确认 FastAPI 已运行在 127.0.0.1:8000。"
      );
    } finally {
      setLoading(false);
    }
  }

  async function openRun(
    runId: string
  ) {
    try {
      setDetailLoading(true);

      const result =
        await getRunDetail(runId);

      setSelectedRun(result);
    } catch (err) {
      console.error(err);

      alert("获取运行详情失败");
    } finally {
      setDetailLoading(false);
    }
  }

  async function loadResources() {
    try {
      setResourceLoading(true);
      setError("");

      const sourceRuns =
        await fetchFreshRuns();

      const details =
        await Promise.all(
          sourceRuns.map(
            async (run) => {
              try {
                return await getRunDetail(
                  run.run_id
                );
              } catch (err) {
                console.error(
                  `读取 ${run.run_id} 失败`,
                  err
                );

                return null;
              }
            }
          )
        );

      const rows: ResourceRow[] = [];

      details.forEach((detail) => {
        if (!detail) {
          return;
        }

        const data =
          detail as RunDetail & {
            optimization_items?: any[];
          };

        (
          data.optimization_items || []
        ).forEach((item) => {
          rows.push({
            run_id:
              data.run_id,

            resource_id:
              String(
                item.resource_id || "--"
              ),

            service:
              String(
                item.service || "--"
              ),

            env:
              String(
                item.env || "--"
              ),

            owner:
              String(
                item.owner || "--"
              ),

            region:
              String(
                item.region || "--"
              ),

            avg_cpu_utilization:
              Number(
                item.avg_cpu_utilization ||
                  0
              ),

            avg_memory_utilization:
              Number(
                item.avg_memory_utilization ||
                  0
              ),

            avg_disk_utilization:
              Number(
                item.avg_disk_utilization ||
                  0
              ),

            avg_gpu_utilization:
              Number(
                item.avg_gpu_utilization ||
                  0
              ),

            monthly_cost:
              Number(
                item.monthly_cost || 0
              ),

            issue_type:
              String(
                item.issue_type || "--"
              ),

            recommend_action:
              String(
                item.recommend_action ||
                  "--"
              ),

            estimated_monthly_saving:
              Number(
                item.estimated_monthly_saving ||
                  0
              ),

            risk_level:
              String(
                item.risk_level ||
                  "unknown"
              ),

            need_human_approval:
              Boolean(
                item.need_human_approval
              ),

            reason:
              String(
                item.reason || ""
              ),
          });
        });
      });

      setResourceRows(rows);
    } catch (err) {
      console.error(err);

      setError(
        "读取资源中心数据失败。"
      );
    } finally {
      setResourceLoading(false);
    }
  }

  async function loadReports() {
    try {
      setReportLoading(true);
      setError("");

      const sourceRuns =
        await fetchFreshRuns();

      const details =
        await Promise.all(
          sourceRuns.map(
            async (run) => {
              try {
                return await getRunDetail(
                  run.run_id
                );
              } catch (err) {
                console.error(
                  `读取 ${run.run_id} 报告失败`,
                  err
                );

                return null;
              }
            }
          )
        );

      const rows: ReportRow[] = [];

      details.forEach((detail) => {
        if (!detail) {
          return;
        }

        const data =
          detail as RunDetail & {
            reports?: any[];
          };

        (
          data.reports || []
        ).forEach((report) => {
          rows.push({
            run_id:
              data.run_id,

            report_id:
              String(
                report.report_id || "--"
              ),

            report_filename:
              String(
                report.report_filename ||
                  "--"
              ),

            report_path:
              String(
                report.report_path || "--"
              ),

            report_saved:
              Boolean(
                report.report_saved
              ),

            created_at:
              String(
                report.created_at || ""
              ),
          });
        });
      });

      setReportRows(rows);
    } catch (err) {
      console.error(err);

      setError(
        "读取优化报告失败。"
      );
    } finally {
      setReportLoading(false);
    }
  }

  async function navigateTo(
    page: ActivePage
  ) {
    setSelectedRun(null);
    setApprovalMessage("");
    setActivePage(page);

    if (page === "resources") {
      await loadResources();
    }

    if (page === "reports") {
      await loadReports();
    }

    if (
      page === "runs" ||
      page === "approval"
    ) {
      await loadRuns();
    }
  }

  async function refreshCurrentPage() {
    if (activePage === "resources") {
      await loadResources();
      return;
    }

    if (activePage === "reports") {
      await loadReports();
      return;
    }

    await loadRuns();
  }

  async function submitApproval(
    runId: string,
    decision: "approve" | "reject"
  ) {
    try {
      setApprovalBusy(runId);
      setApprovalMessage("");

      const response = await fetch(
        "http://127.0.0.1:8000/agent/approval-decision",
        {
          method: "POST",

          headers: {
            Accept: "application/json",
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            run_id: runId,
            decision,
            operator: "sunshine",

            comment:
              decision === "approve"
                ? "批准本次云资源成本优化方案。"
                : "拒绝本次云资源成本优化方案。",

            approved_scope:
              decision === "approve"
                ? "all_proposed"
                : "none",
          }),
        }
      );

      let data: any = null;

      try {
        data = await response.json();
      } catch {
        data = null;
      }

      if (!response.ok) {
        let detailMessage = "";

        const detail = data?.detail;

        if (typeof detail === "string") {
          detailMessage = detail;
        } else if (Array.isArray(detail)) {
          detailMessage = detail
            .map((item: any) => {
              if (
                item &&
                typeof item === "object"
              ) {
                const location =
                  Array.isArray(item.loc)
                    ? item.loc.join(" → ")
                    : "";

                const message =
                  typeof item.msg === "string"
                    ? item.msg
                    : JSON.stringify(item);

                return location
                  ? `${location}: ${message}`
                  : message;
              }

              return String(item);
            })
            .join("；");
        } else if (
          detail !== undefined &&
          detail !== null
        ) {
          try {
            detailMessage =
              JSON.stringify(detail);
          } catch {
            detailMessage =
              String(detail);
          }
        }

        throw new Error(
          detailMessage ||
            `HTTP ${response.status}`
        );
      }

      setApprovalMessage(
        decision === "approve"
          ? "审批成功：该优化任务已批准并继续执行。"
          : "审批成功：该优化任务已拒绝。"
      );

      setSelectedRun(null);

      await loadRuns();
    } catch (err) {
      console.error(err);

      const message =
        err instanceof Error
          ? err.message
          : "未知错误";

      setApprovalMessage(
        `审批失败：${message}`
      );
    } finally {
      setApprovalBusy(null);
    }
  }

  useEffect(() => {
    void loadRuns();
  }, []);

  const stats = useMemo(() => {
    const completed =
      runs.filter(
        (item) =>
          item.status === "completed"
      ).length;

    const pending =
      runs.filter(
        (item) =>
          item.status ===
          "pending_approval"
      ).length;

    const saving =
      runs.reduce(
        (sum, item) =>
          sum +
          Number(
            item.estimated_monthly_saving ||
              0
          ),
        0
      );

    const avgSavingRate =
      runs.length > 0
        ? runs.reduce(
            (sum, item) =>
              sum +
              Number(
                item.saving_rate || 0
              ),
            0
          ) / runs.length
        : 0;

    return {
      total: runs.length,
      completed,
      pending,
      saving,
      avgSavingRate,
    };
  }, [runs]);

  const pendingRuns =
    useMemo(
      () =>
        runs.filter(
          (item) =>
            item.status ===
            "pending_approval"
        ),
      [runs]
    );

  const resourceStats =
    useMemo(() => {
      const totalCost =
        resourceRows.reduce(
          (sum, item) =>
            sum +
            Number(
              item.monthly_cost || 0
            ),
          0
        );

      const totalSaving =
        resourceRows.reduce(
          (sum, item) =>
            sum +
            Number(
              item.estimated_monthly_saving ||
                0
            ),
          0
        );

      const highRisk =
        resourceRows.filter(
          (item) =>
            item.risk_level.toLowerCase() ===
            "high"
        ).length;

      return {
        total:
          resourceRows.length,
        totalCost,
        totalSaving,
        highRisk,
      };
    }, [resourceRows]);

  function renderTopbar(
    title: string,
    description: string
  ) {
    return (
      <header className="topbar">
        <div>
          <h1>{title}</h1>

          <p>
            {description}
          </p>
        </div>

        <div className="topbar-actions">
          <div className="api-status">
            <span />
            API Online
          </div>

          <button
            className="refresh-button"
            onClick={() =>
              void refreshCurrentPage()
            }
          >
            <RefreshCw
              size={17}
              className={
                loading ||
                resourceLoading ||
                reportLoading
                  ? "spin"
                  : ""
              }
            />

            刷新
          </button>
        </div>
      </header>
    );
  }

  function renderWorkflowPanel() {
    return (
      <div className="panel workflow-panel">
        <div className="panel-header">
          <div>
            <h3>
              Agent Workflow
            </h3>

            <p>
              当前生产化执行链
            </p>
          </div>
        </div>

        <div className="workflow">
          <div className="workflow-item done">
            <span>01</span>

            <div>
              <strong>
                Data Validation
              </strong>

              <small>
                数据校验
              </small>
            </div>

            <CheckCircle2 size={17} />
          </div>

          <div className="workflow-line" />

          <div className="workflow-item done">
            <span>02</span>

            <div>
              <strong>
                Billing Analysis
              </strong>

              <small>
                成本解析
              </small>
            </div>

            <CheckCircle2 size={17} />
          </div>

          <div className="workflow-line" />

          <div className="workflow-item done">
            <span>03</span>

            <div>
              <strong>
                Utilization Agent
              </strong>

              <small>
                利用率诊断
              </small>
            </div>

            <CheckCircle2 size={17} />
          </div>

          <div className="workflow-line" />

          <div className="workflow-item warning">
            <span>04</span>

            <div>
              <strong>
                Risk Control
              </strong>

              <small>
                风险分级
              </small>
            </div>

            <ShieldCheck size={17} />
          </div>

          <div className="workflow-line" />

          <div className="workflow-item agent">
            <span>05</span>

            <div>
              <strong>
                Optimization Agent
              </strong>

              <small>
                DeepSeek
              </small>
            </div>

            <Sparkles size={17} />
          </div>

          <div className="workflow-line" />

          <div className="workflow-item approval">
            <span>06</span>

            <div>
              <strong>
                Human Approval
              </strong>

              <small>
                HITL
              </small>
            </div>

            <ShieldCheck size={17} />
          </div>
        </div>
      </div>
    );
  }

  function renderRunList(
    items: AgentRun[]
  ) {
    if (loading) {
      return (
        <div className="loading-state">
          <RefreshCw
            className="spin"
            size={25}
          />

          正在读取 Agent Runs...
        </div>
      );
    }

    if (items.length === 0) {
      return (
        <div className="empty-state">
          暂无运行记录
        </div>
      );
    }

    return (
      <div className="run-list">
        {items.map((run) => (
          <button
            className="run-row"
            key={run.run_id}
            onClick={() =>
              void openRun(run.run_id)
            }
          >
            <div className="run-main">
              <div className="run-icon">
                <Bot size={18} />
              </div>

              <div>
                <strong>
                  {run.run_id}
                </strong>

                <span>
                  {formatTime(
                    run.created_at
                  )}
                </span>
              </div>
            </div>

            <div className="run-saving">
              <span>
                预计节省
              </span>

              <strong>
                {formatMoney(
                  run.estimated_monthly_saving
                )}
              </strong>
            </div>

            <div>
              <RiskBadge
                risk={
                  run.max_risk_level
                }
              />
            </div>

            <div>
              <StatusBadge
                status={
                  run.status
                }
              />
            </div>

            <ChevronRight
              size={17}
              className="run-arrow"
            />
          </button>
        ))}
      </div>
    );
  }

  function renderOverview() {
    return (
      <>
        {renderTopbar(
          "Cloud FinOps 控制台",
          "AI Agent 驱动的云资源成本分析、风险控制与人工审批平台"
        )}

        <section className="hero">
          <div>
            <div className="hero-tag">
              <Bot size={15} />

              CloudCostOps Pro Agent
            </div>

            <h2>
              从成本数据到
              <span>
                {" "}
                可执行优化决策
              </span>
            </h2>

            <p>
              自动完成账单分析、
              资源利用率诊断、
              风险评估、
              成本优化方案生成以及
              Human-in-the-loop
              人工审批。
            </p>
          </div>

          <div className="hero-engine">
            <div className="engine-circle">
              <Bot size={38} />
            </div>

            <div>
              <span>
                Workflow Engine
              </span>

              <strong>
                LangGraph
              </strong>

              <small>
                DeepSeek ·
                Human Approval
              </small>
            </div>
          </div>
        </section>

        {error && (
          <div className="error-box">
            {error}
          </div>
        )}

        <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">
              <Activity size={21} />
            </div>

            <div className="stat-info">
              <span>
                Agent Runs
              </span>

              <strong>
                {stats.total}
              </strong>

              <small>
                已记录的工作流
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <CircleDollarSign
                size={21}
              />
            </div>

            <div className="stat-info">
              <span>
                预计月节省
              </span>

              <strong>
                {formatMoney(
                  stats.saving
                )}
              </strong>

              <small>
                AI 推荐优化价值
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <Gauge size={21} />
            </div>

            <div className="stat-info">
              <span>
                平均节省率
              </span>

              <strong>
                {stats.avgSavingRate.toFixed(
                  1
                )}
                %
              </strong>

              <small>
                历史分析结果
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <ShieldCheck
                size={21}
              />
            </div>

            <div className="stat-info">
              <span>
                待人工审批
              </span>

              <strong>
                {stats.pending}
              </strong>

              <small>
                高风险优化任务
              </small>
            </div>
          </div>
        </section>

        <section className="content-grid">
          <div className="panel runs-panel">
            <div className="panel-header">
              <div>
                <h3>
                  最近 Agent Runs
                </h3>

                <p>
                  数据库持久化的工作流执行记录
                </p>
              </div>

              <button
                className="text-button"
                onClick={() =>
                  void navigateTo(
                    "runs"
                  )
                }
              >
                查看全部

                <ChevronRight
                  size={16}
                />
              </button>
            </div>

            {renderRunList(
              runs.slice(0, 8)
            )}
          </div>

          {renderWorkflowPanel()}
        </section>
      </>
    );
  }

  function renderRunsPage() {
    return (
      <>
        {renderTopbar(
          "Agent Runs",
          "查看 CloudCostOps Agent 的全部历史工作流执行记录与运行详情"
        )}

        {error && (
          <div className="error-box">
            {error}
          </div>
        )}

        <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">
              <Activity size={21} />
            </div>

            <div className="stat-info">
              <span>
                总运行数
              </span>

              <strong>
                {stats.total}
              </strong>

              <small>
                Agent 工作流记录
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <CheckCircle2
                size={21}
              />
            </div>

            <div className="stat-info">
              <span>
                已完成
              </span>

              <strong>
                {stats.completed}
              </strong>

              <small>
                完整执行工作流
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <ShieldCheck
                size={21}
              />
            </div>

            <div className="stat-info">
              <span>
                待审批
              </span>

              <strong>
                {stats.pending}
              </strong>

              <small>
                Human-in-the-loop
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <CircleDollarSign
                size={21}
              />
            </div>

            <div className="stat-info">
              <span>
                优化价值
              </span>

              <strong>
                {formatMoney(
                  stats.saving
                )}
              </strong>

              <small>
                预计月节省
              </small>
            </div>
          </div>
        </section>

        <section>
          <div className="panel runs-panel">
            <div className="panel-header">
              <div>
                <h3>
                  全部 Agent Runs
                </h3>

                <p>
                  点击任意 Run 查看
                  Workflow Steps、
                  Optimization Items
                  以及运行状态
                </p>
              </div>

              <button
                className="text-button"
                onClick={() =>
                  void loadRuns()
                }
              >
                刷新数据

                <RefreshCw
                  size={15}
                />
              </button>
            </div>

            {renderRunList(runs)}
          </div>
        </section>
      </>
    );
  }

  function renderApprovalPage() {
    return (
      <>
        {renderTopbar(
          "人工审批中心",
          "处理 Risk Control Agent 标记的高风险云资源优化任务"
        )}

        {approvalMessage && (
          <div
            className={
              approvalMessage.startsWith(
                "审批失败"
              )
                ? "error-box"
                : "api-status"
            }
            style={{
              marginBottom: 18,
              padding: 14,
            }}
          >
            {approvalMessage}
          </div>
        )}

        <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">
              <ShieldCheck
                size={21}
              />
            </div>

            <div className="stat-info">
              <span>
                待审批任务
              </span>

              <strong>
                {pendingRuns.length}
              </strong>

              <small>
                pending_approval
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <CircleDollarSign
                size={21}
              />
            </div>

            <div className="stat-info">
              <span>
                待审批优化价值
              </span>

              <strong>
                {formatMoney(
                  pendingRuns.reduce(
                    (sum, run) =>
                      sum +
                      Number(
                        run.estimated_monthly_saving ||
                          0
                      ),
                    0
                  )
                )}
              </strong>

              <small>
                预计月节省
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <Bot size={21} />
            </div>

            <div className="stat-info">
              <span>
                Workflow
              </span>

              <strong>
                LangGraph
              </strong>

              <small>
                Human-in-the-loop
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <Sparkles size={21} />
            </div>

            <div className="stat-info">
              <span>
                LLM
              </span>

              <strong>
                DeepSeek
              </strong>

              <small>
                优化方案生成
              </small>
            </div>
          </div>
        </section>

        <section>
          <div className="panel runs-panel">
            <div className="panel-header">
              <div>
                <h3>
                  Pending Approval
                </h3>

                <p>
                  点击任务查看资源风险、
                  优化建议以及完整 Agent
                  Workflow，然后进行批准或拒绝
                </p>
              </div>
            </div>

            {pendingRuns.length === 0 ? (
              <div className="empty-state">
                当前没有待人工审批任务
              </div>
            ) : (
              renderRunList(
                pendingRuns
              )
            )}
          </div>
        </section>
      </>
    );
  }

  function renderResourcesPage() {
    return (
      <>
        {renderTopbar(
          "资源中心",
          "统一查看 Agent 识别出的云资源、利用率、成本、风险以及优化动作"
        )}

        {error && (
          <div className="error-box">
            {error}
          </div>
        )}

        <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">
              <ServerCog size={21} />
            </div>

            <div className="stat-info">
              <span>
                资源记录
              </span>

              <strong>
                {resourceStats.total}
              </strong>

              <small>
                已识别优化资源
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <CircleDollarSign
                size={21}
              />
            </div>

            <div className="stat-info">
              <span>
                当前月成本
              </span>

              <strong>
                {formatMoney(
                  resourceStats.totalCost
                )}
              </strong>

              <small>
                资源成本合计
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <Sparkles size={21} />
            </div>

            <div className="stat-info">
              <span>
                可优化价值
              </span>

              <strong>
                {formatMoney(
                  resourceStats.totalSaving
                )}
              </strong>

              <small>
                预计月节省
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <ShieldCheck
                size={21}
              />
            </div>

            <div className="stat-info">
              <span>
                高风险项
              </span>

              <strong>
                {resourceStats.highRisk}
              </strong>

              <small>
                需要风险控制
              </small>
            </div>
          </div>
        </section>

        <section>
          <div className="panel">
            <div className="panel-header">
              <div>
                <h3>
                  Cloud Resources
                </h3>

                <p>
                  数据来源于各 Agent Run
                  中持久化的 Optimization
                  Items
                </p>
              </div>
            </div>

            {resourceLoading ? (
              <div className="loading-state">
                <RefreshCw
                  size={25}
                  className="spin"
                />

                正在聚合云资源数据...
              </div>
            ) : resourceRows.length ===
              0 ? (
              <div className="empty-state">
                暂无资源优化记录
              </div>
            ) : (
              <div
                style={{
                  overflowX: "auto",
                }}
              >
                <table
                  style={{
                    width: "100%",
                    minWidth: 1250,
                    borderCollapse:
                      "collapse",
                    color: "#dce7ff",
                    fontSize: 13,
                  }}
                >
                  <thead>
                    <tr
                      style={{
                        color: "#7891b8",
                        textAlign: "left",
                      }}
                    >
                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        资源
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        服务
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        Owner
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        环境
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        Region
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        CPU
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        内存
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        磁盘
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        月成本
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        推荐动作
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        预计节省
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        风险
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        Run
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {resourceRows.map(
                      (
                        resource,
                        index
                      ) => (
                        <tr
                          key={`${resource.run_id}-${resource.resource_id}-${index}`}
                          style={{
                            borderTop:
                              "1px solid rgba(100, 140, 200, 0.12)",
                          }}
                        >
                          <td
                            style={{
                              padding: 14,
                              fontWeight: 700,
                            }}
                          >
                            {
                              resource.resource_id
                            }
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            {
                              resource.service
                            }
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            {
                              resource.owner
                            }
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            {
                              resource.env
                            }
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            {
                              resource.region
                            }
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            {formatPercent(
                              resource.avg_cpu_utilization
                            )}
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            {formatPercent(
                              resource.avg_memory_utilization
                            )}
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            {formatPercent(
                              resource.avg_disk_utilization
                            )}
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            {formatMoney(
                              resource.monthly_cost
                            )}
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            {
                              resource.recommend_action
                            }
                          </td>

                          <td
                            style={{
                              padding: 14,
                              fontWeight: 700,
                            }}
                          >
                            {formatMoney(
                              resource.estimated_monthly_saving
                            )}
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            <RiskBadge
                              risk={
                                resource.risk_level
                              }
                            />
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            <button
                              className="text-button"
                              onClick={() =>
                                void openRun(
                                  resource.run_id
                                )
                              }
                            >
                              查看
                            </button>
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      </>
    );
  }

  function renderReportsPage() {
    return (
      <>
        {renderTopbar(
          "优化报告",
          "集中查看 CloudCostOps Agent 自动生成并持久化保存的成本优化报告"
        )}

        {error && (
          <div className="error-box">
            {error}
          </div>
        )}

        <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">
              <FileChartColumn
                size={21}
              />
            </div>

            <div className="stat-info">
              <span>
                已生成报告
              </span>

              <strong>
                {reportRows.length}
              </strong>

              <small>
                Cost Report
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <CheckCircle2
                size={21}
              />
            </div>

            <div className="stat-info">
              <span>
                已保存
              </span>

              <strong>
                {
                  reportRows.filter(
                    (item) =>
                      item.report_saved
                  ).length
                }
              </strong>

              <small>
                本地持久化报告
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <CircleDollarSign
                size={21}
              />
            </div>

            <div className="stat-info">
              <span>
                总优化价值
              </span>

              <strong>
                {formatMoney(
                  stats.saving
                )}
              </strong>

              <small>
                Agent Runs
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <Gauge size={21} />
            </div>

            <div className="stat-info">
              <span>
                平均节省率
              </span>

              <strong>
                {stats.avgSavingRate.toFixed(
                  1
                )}
                %
              </strong>

              <small>
                历史分析结果
              </small>
            </div>
          </div>
        </section>

        <section>
          <div className="panel">
            <div className="panel-header">
              <div>
                <h3>
                  Optimization Reports
                </h3>

                <p>
                  Agent Workflow 自动生成的
                  Markdown 成本优化报告
                </p>
              </div>
            </div>

            {reportLoading ? (
              <div className="loading-state">
                <RefreshCw
                  size={25}
                  className="spin"
                />

                正在读取优化报告...
              </div>
            ) : reportRows.length ===
              0 ? (
              <div className="empty-state">
                暂无已生成的优化报告
              </div>
            ) : (
              <div
                style={{
                  overflowX: "auto",
                }}
              >
                <table
                  style={{
                    width: "100%",
                    minWidth: 1000,
                    borderCollapse:
                      "collapse",
                    color: "#dce7ff",
                    fontSize: 13,
                  }}
                >
                  <thead>
                    <tr
                      style={{
                        color: "#7891b8",
                        textAlign: "left",
                      }}
                    >
                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        Report ID
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        文件名
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        Run ID
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        状态
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        创建时间
                      </th>

                      <th
                        style={{
                          padding: 14,
                        }}
                      >
                        操作
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {reportRows.map(
                      (
                        report,
                        index
                      ) => (
                        <tr
                          key={`${report.report_id}-${index}`}
                          style={{
                            borderTop:
                              "1px solid rgba(100, 140, 200, 0.12)",
                          }}
                        >
                          <td
                            style={{
                              padding: 14,
                              fontWeight: 700,
                            }}
                          >
                            {
                              report.report_id
                            }
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            {
                              report.report_filename
                            }
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            {
                              report.run_id
                            }
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            {report.report_saved ? (
                              <span className="badge badge-success">
                                已保存
                              </span>
                            ) : (
                              <span className="badge badge-warning">
                                未保存
                              </span>
                            )}
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            {formatTime(
                              report.created_at
                            )}
                          </td>

                          <td
                            style={{
                              padding: 14,
                            }}
                          >
                            <button
                              className="text-button"
                              onClick={() =>
                                void openRun(
                                  report.run_id
                                )
                              }
                            >
                              查看 Run

                              <ChevronRight
                                size={14}
                              />
                            </button>
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      </>
    );
  }

  function renderCurrentPage() {
    switch (activePage) {
      case "overview":
        return renderOverview();

      case "optimization":
        return (
          <CostOptimization />
        );

      case "runs":
        return renderRunsPage();

      case "approval":
        return renderApprovalPage();

      case "resources":
        return renderResourcesPage();

      case "reports":
        return renderReportsPage();

      default:
        return renderOverview();
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <CloudCog size={24} />
          </div>

          <div>
            <div className="brand-name">
              CloudCostOps
            </div>

            <div className="brand-subtitle">
              AI FinOps Platform
            </div>
          </div>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-label">
            WORKSPACE
          </div>

          <button
            className={`nav-item ${
              activePage === "overview"
                ? "active"
                : ""
            }`}
            onClick={() =>
              void navigateTo("overview")
            }
          >
            <LayoutDashboard
              size={18}
            />

            <span>
              总览
            </span>
          </button>

          <button
            className={`nav-item ${
              activePage ===
              "optimization"
                ? "active"
                : ""
            }`}
            onClick={() =>
              void navigateTo(
                "optimization"
              )
            }
          >
            <Sparkles size={18} />

            <span>
              成本优化分析
            </span>
          </button>

          <button
            className={`nav-item ${
              activePage === "runs"
                ? "active"
                : ""
            }`}
            onClick={() =>
              void navigateTo("runs")
            }
          >
            <Activity size={18} />

            <span>
              Agent Runs
            </span>
          </button>

          <button
            className={`nav-item ${
              activePage === "approval"
                ? "active"
                : ""
            }`}
            onClick={() =>
              void navigateTo(
                "approval"
              )
            }
          >
            <ShieldCheck
              size={18}
            />

            <span>
              人工审批
            </span>

            {stats.pending > 0 && (
              <span className="nav-count">
                {stats.pending}
              </span>
            )}
          </button>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-label">
            SYSTEM
          </div>

          <button
            className={`nav-item ${
              activePage === "resources"
                ? "active"
                : ""
            }`}
            onClick={() =>
              void navigateTo(
                "resources"
              )
            }
          >
            <ServerCog size={18} />

            <span>
              资源中心
            </span>
          </button>

          <button
            className={`nav-item ${
              activePage === "reports"
                ? "active"
                : ""
            }`}
            onClick={() =>
              void navigateTo(
                "reports"
              )
            }
          >
            <FileChartColumn
              size={18}
            />

            <span>
              优化报告
            </span>
          </button>
        </div>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="system-dot" />

            <div>
              <div className="system-title">
                Agent Engine Online
              </div>

              <div className="system-subtitle">
                LangGraph · DeepSeek
              </div>
            </div>
          </div>
        </div>
      </aside>

      <main className="main">
        {renderCurrentPage()}

        {selectedRun && (
          <div
            className="modal-backdrop"
            onClick={() =>
              setSelectedRun(null)
            }
          >
            <div
              className="detail-modal"
              onClick={(event) =>
                event.stopPropagation()
              }
            >
              <div className="detail-header">
                <div>
                  <span>
                    Agent Run Detail
                  </span>

                  <h3>
                    {selectedRun.run_id}
                  </h3>
                </div>

                <button
                  onClick={() =>
                    setSelectedRun(
                      null
                    )
                  }
                >
                  ×
                </button>
              </div>

              <div className="detail-grid">
                <div>
                  <span>
                    状态
                  </span>

                  <StatusBadge
                    status={
                      selectedRun.status
                    }
                  />
                </div>

                <div>
                  <span>
                    工作流
                  </span>

                  <strong>
                    {selectedRun.workflow_engine ||
                      "--"}
                  </strong>
                </div>

                <div>
                  <span>
                    LLM
                  </span>

                  <strong>
                    {selectedRun.llm_model ||
                      "--"}
                  </strong>
                </div>

                <div>
                  <span>
                    最高风险
                  </span>

                  <RiskBadge
                    risk={
                      selectedRun.max_risk_level
                    }
                  />
                </div>

                <div>
                  <span>
                    预计月节省
                  </span>

                  <strong>
                    {formatMoney(
                      selectedRun.estimated_monthly_saving
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    节省率
                  </span>

                  <strong>
                    {Number(
                      selectedRun.saving_rate ||
                        0
                    ).toFixed(2)}
                    %
                  </strong>
                </div>
              </div>

              <div className="detail-section">
                <div className="detail-section-title">
                  <Timer size={17} />

                  Workflow Steps
                </div>

                <div className="step-list">
                  {selectedRun.workflow_steps?.map(
                    (
                      step,
                      index
                    ) => (
                      <div
                        className="step-card"
                        key={`${step.step_id}-${index}`}
                      >
                        <div className="step-index">
                          {step.step_id ??
                            index + 1}
                        </div>

                        <div className="step-content">
                          <div>
                            <strong>
                              {
                                step.agent_name
                              }
                            </strong>

                            <StatusBadge
                              status={
                                step.status
                              }
                            />
                          </div>

                          <p>
                            {
                              step.action
                            }
                          </p>

                          <small>
                            {
                              step.key_output
                            }
                          </small>
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>

              <div className="detail-section">
                <div className="detail-section-title">
                  <CircleDollarSign
                    size={17}
                  />

                  Optimization Items
                </div>

                <div className="optimization-list">
                  {selectedRun.optimization_items?.map(
                    (
                      item,
                      index
                    ) => (
                      <div
                        className="optimization-card"
                        key={`${item.resource_id}-${index}`}
                      >
                        <div>
                          <strong>
                            {
                              item.resource_id
                            }
                          </strong>

                          <span>
                            {
                              item.service
                            }
                            {" · "}
                            {
                              item.env
                            }
                          </span>
                        </div>

                        <div>
                          <span>
                            推荐动作
                          </span>

                          <strong>
                            {
                              item.recommend_action
                            }
                          </strong>
                        </div>

                        <div>
                          <span>
                            预计节省
                          </span>

                          <strong>
                            {formatMoney(
                              item.estimated_monthly_saving
                            )}
                          </strong>
                        </div>

                        <RiskBadge
                          risk={
                            item.risk_level
                          }
                        />
                      </div>
                    )
                  )}
                </div>
              </div>

              {selectedRun.status ===
                "pending_approval" && (
                <div className="detail-section">
                  <div className="detail-section-title">
                    <ShieldCheck
                      size={17}
                    />

                    Human Approval
                  </div>

                  <p
                    style={{
                      color:
                        "#8da2c7",
                      marginBottom: 16,
                      lineHeight: 1.7,
                    }}
                  >
                    当前任务包含高风险云资源优化动作，
                    需要人工确认后工作流才能继续执行。
                  </p>

                  <div
                    style={{
                      display: "flex",
                      gap: 12,
                      flexWrap: "wrap",
                    }}
                  >
                    <button
                      type="button"
                      disabled={
                        approvalBusy ===
                        selectedRun.run_id
                      }
                      onClick={() =>
                        void submitApproval(
                          selectedRun.run_id,
                          "approve"
                        )
                      }
                      style={{
                        border: 0,
                        borderRadius: 8,
                        padding:
                          "10px 20px",
                        fontWeight: 700,
                        cursor: "pointer",
                        color: "#ffffff",
                        background:
                          "linear-gradient(135deg, #315cff, #7c4dff)",
                        opacity:
                          approvalBusy ===
                          selectedRun.run_id
                            ? 0.6
                            : 1,
                      }}
                    >
                      {approvalBusy ===
                      selectedRun.run_id
                        ? "处理中..."
                        : "批准优化方案"}
                    </button>

                    <button
                      type="button"
                      disabled={
                        approvalBusy ===
                        selectedRun.run_id
                      }
                      onClick={() =>
                        void submitApproval(
                          selectedRun.run_id,
                          "reject"
                        )
                      }
                      style={{
                        border:
                          "1px solid rgba(255, 90, 110, 0.45)",
                        borderRadius: 8,
                        padding:
                          "10px 20px",
                        fontWeight: 700,
                        cursor: "pointer",
                        color: "#ff7384",
                        background:
                          "rgba(255, 70, 90, 0.08)",
                        opacity:
                          approvalBusy ===
                          selectedRun.run_id
                            ? 0.6
                            : 1,
                      }}
                    >
                      拒绝优化方案
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {detailLoading && (
          <div className="detail-loading">
            <RefreshCw
              size={22}
              className="spin"
            />

            正在读取 Run Detail...
          </div>
        )}
      </main>
    </div>
  );
}

export default App;