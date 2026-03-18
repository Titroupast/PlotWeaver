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

export type ChapterLatestContent = {
  chapter_id: string;
  version_no: number;
  storage_bucket: string;
  storage_key: string;
  content_sha256: string;
  byte_size: number;
  content: string;
  created_at: string;
};

export type ChapterVersion = {
  chapter_id: string;
  version_no: number;
  run_id: string | null;
  version_title: string | null;
  storage_bucket: string;
  storage_key: string;
  content_sha256: string;
  byte_size: number;
  created_at: string;
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
  cursor?: string | null;
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

export type MemorySnapshotItem = {
  memory_type: string;
  version_no: number;
  summary_json: Record<string, unknown> | unknown[] | null;
  updated_at: string;
};

export type MemorySnapshotResponse = {
  project_id: string;
  snapshots: MemorySnapshotItem[];
};

export type MemoryDelta = {
  id: string;
  run_id: string;
  project_id: string;
  delta_type: string;
  payload_json: Record<string, unknown>;
  gate_status: string;
  risk_level: string;
  applied_at: string | null;
  applied_by: string | null;
  created_at: string;
};

export type MergeDecision = {
  id: string;
  project_id: string;
  run_id: string | null;
  delta_id: string | null;
  decision_type: string;
  payload_json: Record<string, unknown>;
  reason: string | null;
  created_at: string;
};

export type MemoryDeltaDecisionResponse = {
  delta: MemoryDelta;
  merge_decision: MergeDecision | null;
};

export type MemoryHistoryItem = {
  id: string;
  memory_type: string;
  version_no: number;
  summary_json: Record<string, unknown> | unknown[] | null;
  created_at: string;
  updated_at: string;
};

export type MemoryRebuildResponse = {
  project_id: string;
  updated_types: string[];
  versions: Record<string, number>;
  sources: Record<string, string>;
  reasons: Record<string, string>;
  chapter_count: number;
};

export type ProjectImportResponse = {
  project: Project;
  chapter_count: number;
};

