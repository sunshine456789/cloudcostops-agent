import {
  useMemo,
  useState,
} from "react";

import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  CloudCog,
  FileSpreadsheet,
  Loader2,
  Play,
  ShieldAlert,
  Sparkles,
  UploadCloud,
} from "lucide-react";

import api, {
  getRunDetail,
} from "../api/cloudcost";

import "./CostOptimization.css";


type WorkflowStep = {
  step_id?: number;

  agent_name?: string;

  stage?: string;

  status?: string;

  status_label?: string;

  duration_ms?: number;

  action?: string;

  key_output?: string;

  evidence?: unknown;
};


type OptimizationItem = {
  resource_id?: string;

  service?: string;

  env?: string;

  owner?: string;

  region?: string;

  avg_cpu_utilization?: number;

  avg_memory_utilization?: number;

  avg_disk_utilization?: number;

  avg_gpu_utilization?: number;

  monthly_cost?: number;

  issue_type?: string;

  recommend_action?: string;

  estimated_monthly_saving?: number;

  risk_level?: string;

  need_human_approval?: boolean;

  reason?: string;
};


type OptimizationResponse = {
  success?: boolean;

  run_id?: string;

  status?: string | null;

  workflow_engine?:
    | string
    | null;

  llm_enabled?:
    | boolean
    | null;

  llm_model?:
    | string
    | null;

  llm_error?:
    | string
    | null;

  estimated_monthly_saving?:
    | number
    | null;

  saving_rate?:
    | number
    | null;

  max_risk_level?:
    | string
    | null;

  approval_required?:
    | boolean
    | null;

  approval_decision?:
    | string
    | null;

  approval_operator?:
    | string
    | null;

  approval_comment?:
    | string
    | null;

  approved_scope?:
    | string
    | null;

  total_elapsed_time?:
    | number
    | null;

  workflow_steps?:
    WorkflowStep[];

  optimization_items?:
    OptimizationItem[];

  report_id?:
    string;

  report_filename?:
    string;

  report_path?:
    string;

  report_saved?:
    boolean;

  markdown_report?:
    string;
};


function money(
  value?: number | null
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "¥0";
  }

  return `¥${Number(
    value
  ).toLocaleString(
    "zh-CN",
    {
      maximumFractionDigits: 2,
    }
  )}`;
}


function percentage(
  value?: number | null
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "0.0%";
  }

  return `${Number(
    value
  ).toFixed(1)}%`;
}


function riskText(
  risk?: string | null
) {
  const value = (
    risk || ""
  ).toLowerCase();

  if (value === "high") {
    return "高风险";
  }

  if (value === "medium") {
    return "中风险";
  }

  if (value === "low") {
    return "低风险";
  }

  return risk || "-";
}


function statusText(
  status?: string | null
) {
  switch (status) {
    case "pending_approval":
      return "待人工审批";

    case "completed":
      return "已完成";

    case "rejected":
      return "已拒绝";

    case "failed":
      return "执行失败";

    case "running":
      return "执行中";

    default:
      return status || "-";
  }
}


export default function CostOptimization() {
  const [
    billingFile,
    setBillingFile,
  ] =
    useState<File | null>(
      null
    );

  const [
    utilizationFile,
    setUtilizationFile,
  ] =
    useState<File | null>(
      null
    );

  const [
    loading,
    setLoading,
  ] =
    useState(false);

  const [
    error,
    setError,
  ] =
    useState("");

  const [
    result,
    setResult,
  ] =
    useState<OptimizationResponse | null>(
      null
    );


  const canRun =
    useMemo(
      () => {
        return Boolean(
          billingFile &&
            utilizationFile &&
            !loading
        );
      },
      [
        billingFile,
        utilizationFile,
        loading,
      ]
    );


  async function handleRun() {
    if (
      !billingFile ||
      !utilizationFile
    ) {
      setError(
        "请先选择账单文件和资源利用率文件。"
      );

      return;
    }

    try {
      setLoading(true);

      setError("");

      setResult(null);


      const formData =
        new FormData();

      formData.append(
        "billing_file",
        billingFile
      );

      formData.append(
        "utilization_file",
        utilizationFile
      );


      /*
       * 第一步：
       *
       * 启动 LangGraph 多 Agent
       * FinOps 成本优化工作流。
       */
      const response =
        await api.post(
          "/agent/optimization-plan",
          formData,
          {
            headers: {
              "Content-Type":
                "multipart/form-data",
            },

            timeout: 180000,
          }
        );


      const initialResult =
        response.data as OptimizationResponse;


      console.log(
        "[CloudCostOps] optimization-plan response:",
        initialResult
      );


      /*
       * 第二步：
       *
       * optimization-plan 接口主要负责
       * 启动并执行工作流。
       *
       * 完整的：
       *
       * workflow_steps
       * optimization_items
       * approvals
       * reports
       *
       * 最终会保存到 Agent Run。
       *
       * 因此这里拿到 run_id 之后，
       * 再调用：
       *
       * GET /runs/{run_id}
       *
       * 查询数据库中的完整 Run Detail。
       */
      if (
        initialResult?.run_id
      ) {
        try {
          const detail =
            await getRunDetail(
              initialResult.run_id
            );


          console.log(
            "[CloudCostOps] full run detail:",
            detail
          );


          const latestReport =
            detail.reports &&
            detail.reports.length >
              0
              ? detail.reports[0]
              : undefined;


          /*
           * Run Detail 是最终持久化结果。
           *
           * 将 POST 即时响应和
           * GET Run Detail 合并。
           *
           * 其中 optimization_items
           * 明确优先使用 Run Detail。
           */
          const mergedResult: OptimizationResponse =
            {
              ...initialResult,

              success:
                detail.success ??
                initialResult.success,

              run_id:
                detail.run_id ??
                initialResult.run_id,

              status:
                detail.status ??
                initialResult.status,

              workflow_engine:
                detail.workflow_engine ??
                initialResult.workflow_engine,

              llm_enabled:
                detail.llm_enabled ??
                initialResult.llm_enabled,

              llm_model:
                detail.llm_model ??
                initialResult.llm_model,

              llm_error:
                detail.llm_error ??
                initialResult.llm_error,

              estimated_monthly_saving:
                detail.estimated_monthly_saving ??
                initialResult.estimated_monthly_saving,

              saving_rate:
                detail.saving_rate ??
                initialResult.saving_rate,

              max_risk_level:
                detail.max_risk_level ??
                initialResult.max_risk_level,

              approval_required:
                detail.approval_required ??
                initialResult.approval_required,

              approval_decision:
                detail.approval_decision ??
                initialResult.approval_decision,

              approval_operator:
                detail.approval_operator ??
                initialResult.approval_operator,

              approved_scope:
                detail.approved_scope ??
                initialResult.approved_scope,

              total_elapsed_time:
                detail.total_elapsed_time ??
                initialResult.total_elapsed_time,


              workflow_steps:
                detail.workflow_steps ??
                initialResult.workflow_steps ??
                [],


              /*
               * 核心修复：
               *
               * Swagger 中已经证明
               * GET /runs/{run_id}
               * 返回真实 optimization_items。
               */
              optimization_items:
                detail.optimization_items ??
                initialResult.optimization_items ??
                [],


              /*
               * Run Detail 返回 reports 数组，
               * 当前页面使用扁平字段，
               * 所以这里进行兼容转换。
               */
              report_id:
                latestReport?.report_id ??
                initialResult.report_id,

              report_filename:
                latestReport?.report_filename ??
                initialResult.report_filename,

              report_path:
                latestReport?.report_path ??
                initialResult.report_path,

              report_saved:
                latestReport?.report_saved ??
                initialResult.report_saved ??
                false,

              markdown_report:
                initialResult.markdown_report,
            };


          console.log(
            "[CloudCostOps] merged frontend result:",
            mergedResult
          );

          console.log(
            "[CloudCostOps] optimization_items:",
            mergedResult.optimization_items
          );


          setResult(
            mergedResult
          );
        } catch (
          detailError
        ) {
          /*
           * Run Detail 查询失败时，
           * 不影响 POST 主流程结果显示。
           */
          console.warn(
            "[CloudCostOps] failed to load run detail:",
            detailError
          );

          setResult(
            initialResult
          );
        }
      } else {
        console.warn(
          "[CloudCostOps] response has no run_id."
        );

        setResult(
          initialResult
        );
      }
    } catch (err: any) {
      console.error(
        "CloudCostOps optimization error:",
        err
      );


      const detail =
        err?.response?.data
          ?.detail ||
        err?.response?.data
          ?.message ||
        err?.message ||
        "AI 成本优化任务执行失败。";


      if (
        typeof detail ===
        "string"
      ) {
        setError(detail);
      } else {
        setError(
          JSON.stringify(
            detail
          )
        );
      }
    } finally {
      setLoading(false);
    }
  }


  return (
    <div className="cost-page">

      {/* 页面标题 */}
      <div className="cost-page-header">

        <div>

          <div className="cost-page-eyebrow">

            <CloudCog
              size={15}
            />

            CloudCostOps AI Optimization

          </div>


          <h1>
            成本优化分析
          </h1>


          <p>
            上传云账单和资源利用率数据，
            由 LangGraph 多 Agent
            自动完成成本识别、资源分析、
            风险控制以及 AI 优化决策。
          </p>

        </div>


        <div className="engine-card">

          <div className="engine-icon">

            <Bot
              size={23}
            />

          </div>


          <div>

            <span>
              WORKFLOW ENGINE
            </span>

            <strong>
              LangGraph
            </strong>

            <small>
              DeepSeek · Human Approval
            </small>

          </div>

        </div>

      </div>


      {/* 上传区域 */}
      <section className="cost-section">

        <div className="section-heading">

          <div>

            <h2>
              01 · 上传分析数据
            </h2>

            <p>
              系统需要账单数据以及资源利用率数据
              作为 FinOps 优化分析输入。
            </p>

          </div>

        </div>


        <div className="upload-grid">

          {/* Billing */}
          <label className="upload-card">

            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(
                event
              ) => {
                setBillingFile(
                  event.target
                    .files?.[0] ||
                    null
                );

                setError("");
              }}
            />


            <div className="upload-icon">

              <FileSpreadsheet
                size={25}
              />

            </div>


            <div className="upload-content">

              <div className="upload-label">
                Cloud Billing
              </div>


              <h3>
                云账单数据
              </h3>


              <p>
                上传资源费用、服务类型、
                环境、Owner 等云成本数据。
              </p>


              <div
                className={
                  billingFile
                    ? "file-selected"
                    : "file-empty"
                }
              >
                {billingFile
                  ? billingFile.name
                  : "选择 cloud_billing_sample.csv"}
              </div>

            </div>


            <UploadCloud
              size={20}
              className="upload-arrow"
            />

          </label>


          {/* Utilization */}
          <label className="upload-card">

            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(
                event
              ) => {
                setUtilizationFile(
                  event.target
                    .files?.[0] ||
                    null
                );

                setError("");
              }}
            />


            <div className="upload-icon">

              <ActivityIcon />

            </div>


            <div className="upload-content">

              <div className="upload-label">
                Resource Utilization
              </div>


              <h3>
                资源利用率数据
              </h3>


              <p>
                上传 CPU、内存、磁盘、
                GPU 等资源利用率数据。
              </p>


              <div
                className={
                  utilizationFile
                    ? "file-selected"
                    : "file-empty"
                }
              >
                {utilizationFile
                  ? utilizationFile.name
                  : "选择 cloud_utilization_sample.csv"}
              </div>

            </div>


            <UploadCloud
              size={20}
              className="upload-arrow"
            />

          </label>

        </div>


        <div className="analysis-action">

          <div className="analysis-description">

            <Sparkles
              size={18}
            />


            <span>
              AI 将依次执行 Data Validation →
              Billing Analysis →
              Utilization Agent →
              Risk Control →
              Optimization Agent。
            </span>

          </div>


          <button
            className="run-button"
            disabled={!canRun}
            onClick={
              handleRun
            }
          >

            {loading ? (
              <>

                <Loader2
                  size={18}
                  className="spin"
                />

                AI Agent 正在分析...

              </>
            ) : (
              <>

                <Play
                  size={18}
                />

                开始 AI 成本优化

              </>
            )}

          </button>

        </div>


        {error && (
          <div className="analysis-error">

            <AlertTriangle
              size={18}
            />

            {error}

          </div>
        )}

      </section>


      {/* 加载状态 */}
      {loading && (
        <section className="cost-section">

          <div className="running-panel">

            <div className="running-icon">

              <Loader2
                size={30}
                className="spin"
              />

            </div>


            <h2>
              CloudCostOps Agent
              正在运行
            </h2>


            <p>
              正在执行多 Agent
              成本优化工作流。
              DeepSeek 分析可能需要几十秒，
              请不要关闭页面。
            </p>


            <div className="running-steps">

              <span>
                Data Validation
              </span>

              <i />


              <span>
                Billing Analysis
              </span>

              <i />


              <span>
                Utilization
              </span>

              <i />


              <span>
                Risk Control
              </span>

              <i />


              <span>
                AI Planning
              </span>

            </div>

          </div>

        </section>
      )}


      {/* 分析结果 */}
      {result &&
        !loading && (
          <>

            <section className="result-summary">

              <SummaryCard
                label="Run ID"
                value={
                  result.run_id ||
                  "-"
                }
                small
              />


              <SummaryCard
                label="预计月节省"
                value={money(
                  result.estimated_monthly_saving
                )}
              />


              <SummaryCard
                label="预计节省率"
                value={percentage(
                  result.saving_rate
                )}
              />


              <SummaryCard
                label="最高风险"
                value={riskText(
                  result.max_risk_level
                )}
                danger={
                  result.max_risk_level
                    ?.toLowerCase() ===
                  "high"
                }
              />


              <SummaryCard
                label="任务状态"
                value={statusText(
                  result.status
                )}
                success={
                  result.status ===
                  "completed"
                }
              />

            </section>


            {/* 工作流 */}
            <section className="cost-section">

              <div className="section-heading">

                <div>

                  <h2>
                    02 · Agent Workflow
                  </h2>


                  <p>
                    展示本次 LangGraph
                    多 Agent 工作流的
                    实际执行过程。
                  </p>

                </div>


                <div className="workflow-meta">

                  {result.llm_model && (
                    <span>

                      <Bot
                        size={14}
                      />

                      {
                        result.llm_model
                      }

                    </span>
                  )}


                  <span>
                    {
                      result.workflow_engine ||
                      "langgraph"
                    }
                  </span>

                </div>

              </div>


              <div className="workflow-list">

                {(
                  result.workflow_steps ||
                  []
                ).map(
                  (
                    step,
                    index
                  ) => (
                    <div
                      className="workflow-item"
                      key={`${step.step_id}-${step.agent_name}-${index}`}
                    >

                      <div className="step-number">

                        {String(
                          step.step_id ||
                            index +
                              1
                        ).padStart(
                          2,
                          "0"
                        )}

                      </div>


                      <div className="step-body">

                        <div className="step-top">

                          <div>

                            <strong>
                              {step.agent_name ||
                                step.stage ||
                                "Agent"}
                            </strong>


                            <span>
                              {step.stage ||
                                "-"}
                            </span>

                          </div>


                          <div
                            className={`step-status ${
                              step.status ===
                              "success"
                                ? "success"
                                : step.status ===
                                  "warning"
                                ? "warning"
                                : step.status ===
                                  "pending"
                                ? "pending"
                                : ""
                            }`}
                          >
                            {step.status_label ||
                              step.status ||
                              "-"}
                          </div>

                        </div>


                        {step.action && (
                          <p className="step-action">
                            {
                              step.action
                            }
                          </p>
                        )}


                        {step.key_output && (
                          <div className="step-output">
                            {
                              step.key_output
                            }
                          </div>
                        )}


                        {step.duration_ms !==
                          undefined && (
                          <small>
                            执行耗时：
                            {
                              step.duration_ms
                            }{" "}
                            ms
                          </small>
                        )}

                      </div>

                    </div>
                  )
                )}

              </div>

            </section>


            {/* 优化项 */}
            <section className="cost-section">

              <div className="section-heading">

                <div>

                  <h2>
                    03 · 成本优化建议
                  </h2>


                  <p>
                    根据成本数据和资源利用率
                    识别出的可执行 FinOps
                    优化项。
                  </p>

                </div>


                <span className="optimization-count">

                  {(
                    result.optimization_items ||
                    []
                  ).length}{" "}
                  项

                </span>

              </div>


              <div className="optimization-list">

                {(
                  result.optimization_items ||
                  []
                ).map(
                  (
                    item,
                    index
                  ) => (
                    <div
                      className="optimization-card"
                      key={`${item.resource_id}-${index}`}
                    >

                      <div className="optimization-top">

                        <div>

                          <div className="resource-type">
                            {item.service ||
                              "Cloud Resource"}
                          </div>


                          <h3>
                            {item.resource_id ||
                              `Resource ${
                                index +
                                1
                              }`}
                          </h3>


                          <div className="resource-meta">

                            <span>
                              {item.env ||
                                "-"}
                            </span>

                            <span>
                              {item.owner ||
                                "-"}
                            </span>

                            <span>
                              {item.region ||
                                "-"}
                            </span>

                          </div>

                        </div>


                        <div className="optimization-saving">

                          <span>
                            预计月节省
                          </span>


                          <strong>
                            {money(
                              item.estimated_monthly_saving
                            )}
                          </strong>

                        </div>

                      </div>


                      <div className="metric-row">

                        <Metric
                          label="CPU"
                          value={
                            item.avg_cpu_utilization
                          }
                        />


                        <Metric
                          label="Memory"
                          value={
                            item.avg_memory_utilization
                          }
                        />


                        <Metric
                          label="Disk"
                          value={
                            item.avg_disk_utilization
                          }
                        />


                        <Metric
                          label="GPU"
                          value={
                            item.avg_gpu_utilization
                          }
                        />

                      </div>


                      <div className="optimization-bottom">

                        <div>

                          <span className="issue-label">
                            {item.issue_type ||
                              "-"}
                          </span>


                          <strong>
                            {item.recommend_action ||
                              "-"}
                          </strong>


                          {item.reason && (
                            <p>
                              {
                                item.reason
                              }
                            </p>
                          )}

                        </div>


                        <div className="risk-area">

                          <span
                            className={`risk-tag ${(
                              item.risk_level ||
                              ""
                            ).toLowerCase()}`}
                          >

                            <ShieldAlert
                              size={13}
                            />

                            {riskText(
                              item.risk_level
                            )}

                          </span>


                          {item.need_human_approval && (
                            <span className="approval-tag">
                              需要人工审批
                            </span>
                          )}

                        </div>

                      </div>

                    </div>
                  )
                )}


                {!result
                  .optimization_items
                  ?.length && (
                  <div className="empty-optimization">

                    <CheckCircle2
                      size={30}
                    />


                    <strong>
                      暂未发现需要优化的资源
                    </strong>


                    <span>
                      当前数据中没有返回优化项。
                    </span>

                  </div>
                )}

              </div>

            </section>


            {/* 报告 */}
            {result.report_saved && (
              <section className="report-banner">

                <div className="report-icon">

                  <CheckCircle2
                    size={24}
                  />

                </div>


                <div>

                  <strong>
                    FinOps 优化报告已生成
                  </strong>


                  <span>
                    {result.report_filename ||
                      result.report_id ||
                      "CloudCostOps Report"}
                  </span>

                </div>

              </section>
            )}

          </>
        )}

    </div>
  );
}


function SummaryCard({
  label,
  value,
  small = false,
  danger = false,
  success = false,
}: {
  label: string;

  value: string;

  small?: boolean;

  danger?: boolean;

  success?: boolean;
}) {
  return (
    <div className="summary-card">

      <span>
        {label}
      </span>


      <strong
        className={[
          small
            ? "summary-small"
            : "",

          danger
            ? "summary-danger"
            : "",

          success
            ? "summary-success"
            : "",
        ].join(" ")}
      >
        {value}
      </strong>

    </div>
  );
}


function Metric({
  label,
  value,
}: {
  label: string;

  value?: number;
}) {
  return (
    <div className="metric">

      <span>
        {label}
      </span>


      <strong>
        {value ===
          undefined ||
        value === null
          ? "-"
          : `${Number(
              value
            ).toFixed(1)}%`}
      </strong>

    </div>
  );
}


function ActivityIcon() {
  return (
    <svg
      width="25"
      height="25"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M3 12h4l2-7 4 14 2-7h6" />
    </svg>
  );
}