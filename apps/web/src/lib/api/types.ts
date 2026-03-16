export type Project = {
  id: string;
  tenant_id: string;
  title: string;
  description: string | null;
  language: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Chapter = {
  id: string;
  project_id: string;
  chapter_key: string;
  kind: string;
  title: string;
  order_index: number;
  status: string;
  summary: string;
  created_at: string;
  updated_at: string;
};

export type Requirement = {
  id: string;
  project_id: string;
  chapter_goal: string;
  payload_json: Record<string, unknown>;
  payload_hash: string;
  source: string;
  created_at: string;
};

export type Run = {
  id: string;
  project_id: string;
  state: string;
  idempotency_key: string;
  attempt_count: number;
  retry_count: number;
  current_step: string | null;
  checkpoint_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type RunEvent = {
  id: string;
  run_id: string;
  event_type: string;
  step: string | null;
  payload_json: Record<string, unknown> | null;
  created_at: string;
};

export type Artifact = {
  id: string;
  run_id: string;
  artifact_type: string;
  version_no: number;
  payload_json: Record<string, unknown>;
  payload_hash: string;
  created_at: string;
};
