import { getApiBaseUrl, getTenantId, parseJsonOrThrow } from "@/lib/api/shared";
import type { Artifact, Requirement, Run, RunEvent } from "@/lib/api/types";

function makeHeaders(): HeadersInit {
  return {
    "content-type": "application/json",
    "x-tenant-id": getTenantId()
  };
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${getApiBaseUrl()}${path}`, {
    headers: makeHeaders(),
    cache: "no-store"
  });
  return parseJsonOrThrow<T>(res);
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    headers: makeHeaders(),
    body: JSON.stringify(body),
    cache: "no-store"
  });
  return parseJsonOrThrow<T>(res);
}

export const clientApi = {
  createRequirement: (projectId: string, payload: Record<string, unknown>) =>
    post<Requirement>(`/projects/${projectId}/requirements`, payload),
  createRun: (payload: {
    project_id: string;
    base_chapter_id?: string;
    target_chapter_id?: string;
    requirement_id?: string;
    idempotency_key: string;
  }) => post<Run>("/runs", payload),
  getRun: (runId: string) => get<Run>(`/runs/${runId}`),
  listRunEvents: (runId: string, afterCursor?: string) =>
    get<RunEvent[]>(
      `/runs/${runId}/events?limit=200${afterCursor ? `&after_cursor=${encodeURIComponent(afterCursor)}` : ""}`
    ),
  listArtifacts: (runId: string) => get<Artifact[]>(`/runs/${runId}/artifacts?limit=100`),
  executeRun: (runId: string) => post<Run>(`/runs/${runId}/execute`, {}),
  humanReviewDecision: (runId: string, decision: "APPROVE" | "REQUEST_REWRITE" | "REJECT", reason?: string) =>
    post<Run>(`/runs/${runId}/review-decision`, { decision, reason })
};
