import { getApiBaseUrl, getTenantId, parseJsonOrThrow } from "@/lib/api/shared";
import type {
  Artifact,
  ChapterVersion,
  ChapterLatestContent,
  MemoryDelta,
  MemoryDeltaDecisionResponse,
  MemoryHistoryItem,
  MemoryRebuildResponse,
  MemorySnapshotResponse,
  Project,
  ProjectImportResponse,
  Requirement,
  Run,
  RunEvent
} from "@/lib/api/types";

function makeHeaders(contentType: string | null = "application/json"): HeadersInit {
  const headers: Record<string, string> = {
    "x-tenant-id": getTenantId()
  };
  if (contentType) headers["content-type"] = contentType;
  return headers;
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

async function del(path: string): Promise<void> {
  const res = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "DELETE",
    headers: makeHeaders(),
    cache: "no-store"
  });
  if (!res.ok) {
    await parseJsonOrThrow<unknown>(res);
  }
}

export const clientApi = {
  createProject: (payload: { title: string; description?: string }) => post<Project>("/projects", payload),
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
  getLatestChapterContent: (projectId: string, chapterId: string) =>
    get<ChapterLatestContent>(`/projects/${projectId}/chapters/${chapterId}/latest-content`),
  getChapterContent: (projectId: string, chapterId: string, versionNo?: number) =>
    get<ChapterLatestContent>(
      `/projects/${projectId}/chapters/${chapterId}/content${versionNo ? `?version_no=${versionNo}` : ""}`
    ),
  listChapterVersions: (projectId: string, chapterId: string) =>
    get<ChapterVersion[]>(`/projects/${projectId}/chapters/${chapterId}/versions?limit=100`),
  executeRun: (runId: string, payload?: { auto_continue?: boolean; resume_from_step?: string }) =>
    post<Run>(`/runs/${runId}/execute`, payload ?? {}),
  humanReviewDecision: (runId: string, decision: "APPROVE" | "REQUEST_REWRITE" | "REJECT", reason?: string) =>
    post<Run>(`/runs/${runId}/review-decision`, { decision, reason }),
  getMemorySnapshots: (projectId: string) => get<MemorySnapshotResponse>(`/memory/projects/${projectId}/snapshots`),
  listMemoryDeltas: (projectId: string, status?: string) =>
    get<MemoryDelta[]>(`/memory/projects/${projectId}/deltas?limit=200${status ? `&status=${encodeURIComponent(status)}` : ""}`),
  decideMemoryDelta: (projectId: string, deltaId: string, payload: { decision: "MERGE" | "REJECT"; reason?: string }) =>
    post<MemoryDeltaDecisionResponse>(`/memory/projects/${projectId}/deltas/${deltaId}/decision`, payload),
  listMemoryHistory: (projectId: string) => get<MemoryHistoryItem[]>(`/memory/projects/${projectId}/history?limit=200`),
  rebuildMemorySummary: (projectId: string) => post<MemoryRebuildResponse>(`/memory/projects/${projectId}/rebuild`, {}),
  importProjectFromTxt: async (input: { title: string; description?: string; language?: string; file: File }) => {
    const fd = new FormData();
    fd.append("title", input.title);
    fd.append("description", input.description ?? "");
    fd.append("language", input.language ?? "zh-CN");
    fd.append("file", input.file);

    const res = await fetch(`${getApiBaseUrl()}/projects/import-txt`, {
      method: "POST",
      headers: makeHeaders(null),
      body: fd,
      cache: "no-store"
    });
    return parseJsonOrThrow<ProjectImportResponse>(res);
  },
  deleteProject: (projectId: string) => del(`/projects/${projectId}`)
};
