import axios from "axios";

export const API_BASE_URL = "http://127.0.0.1:8000";


const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: {
    Accept: "application/json",
  },
});


export interface AgentRun {
  run_id: string;
  status: string;

  workflow_engine?: string | null;

  llm_enabled?: boolean | null;
  llm_model?: string | null;
  llm_error?: string | null;

  approval_required?: boolean | null;
  max_risk_level?: string | null;

  approval_decision?: string | null;
  approval_operator?: string | null;
  approval_comment?: string | null;
  approved_scope?: string | null;

  estimated_monthly_saving?: number | null;
  saving_rate?: number | null;

  billing_filename?: string | null;
  utilization_filename?: string | null;

  total_elapsed_time?: number | null;

  started_at?: string | null;
  completed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}


export interface RunsResponse {
  success: boolean;
  total: number;
  page: number;
  page_size: number;
  items: AgentRun[];
}


export interface WorkflowStep {
  step_id?: number;

  agent_name?: string;
  stage?: string;

  status?: string;
  status_label?: string;

  duration_ms?: number;

  action?: string;
  key_output?: string;

  evidence?: unknown;
}


export interface OptimizationItem {
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
}


export interface ApprovalRecord {
  decision?: string;

  operator?: string;

  comment?: string;

  approved_scope?: string;

  created_at?: string;
}


export interface ReportRecord {
  report_id?: string;

  report_filename?: string;

  report_path?: string;

  report_saved?: boolean;

  created_at?: string;
}


export interface RunDetail extends AgentRun {
  success: boolean;

  workflow_steps?: WorkflowStep[];

  optimization_items?: OptimizationItem[];

  approvals?: ApprovalRecord[];

  reports?: ReportRecord[];
}


export async function listRuns(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  approval_required?: boolean;
}): Promise<RunsResponse> {
  const response = await api.get<RunsResponse>(
    "/runs",
    {
      params: {
        page: params?.page ?? 1,

        page_size:
          params?.page_size ?? 20,

        status:
          params?.status || undefined,

        approval_required:
          params?.approval_required,
      },
    }
  );

  return response.data;
}


export async function listPendingRuns(): Promise<unknown> {
  const response = await api.get(
    "/runs/pending"
  );

  return response.data;
}


export async function getRunDetail(
  runId: string
): Promise<RunDetail> {
  const response = await api.get<RunDetail>(
    `/runs/${encodeURIComponent(runId)}`
  );

  return response.data;
}


export async function submitApproval(payload: {
  run_id: string;

  decision:
    | "approve"
    | "reject";

  operator: string;

  comment?: string;

  approved_scope?: string;
}): Promise<unknown> {
  const response = await api.post(
    "/agent/approval-decision",
    payload
  );

  return response.data;
}


export async function generateOptimizationPlan(
  billingFile: File,
  utilizationFile: File
): Promise<unknown> {
  const formData = new FormData();

  formData.append(
    "billing_file",
    billingFile
  );

  formData.append(
    "utilization_file",
    utilizationFile
  );

  const response = await api.post(
    "/agent/optimization-plan",
    formData,
    {
      headers: {
        "Content-Type":
          "multipart/form-data",
      },

      timeout: 300000,
    }
  );

  return response.data;
}


export default api;