import "server-only";

import { getApiBaseUrl, getTenantId, parseJsonOrThrow } from "@/lib/api/shared";
import type { Artifact, Chapter, ChapterLatestContent, Project, Requirement, Run, RunEvent } from "@/lib/api/types";

function makeHeaders(): HeadersInit {
  return {
    "content-type": "application/json",
    "x-tenant-id": getTenantId()
  };
}

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      ...makeHeaders(),
      ...(init?.headers ?? {})
    },
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

export const serverApi = {
  listProjects: () => get<Project[]>("/projects"),
  createProject: (payload: { title: string; description?: string }) => post<Project>("/projects", payload),
  getProject: (projectId: string) => get<Project>(`/projects/${projectId}`),
  listChapters: (projectId: string) => get<Chapter[]>(`/projects/${projectId}/chapters`),
  getLatestChapterContent: (projectId: string, chapterId: string) =>
    get<ChapterLatestContent>(`/projects/${projectId}/chapters/${chapterId}/latest-content`),
  createRequirement: (projectId: string, payload: Record<string, unknown>) =>
    post<Requirement>(`/projects/${projectId}/requirements`, payload),
  createRun: (payload: {
    project_id: string;
    base_chapter_id?: string;
    target_chapter_id?: string;
    requirement_id?: string;
    idempotency_key: string;
  }) => post<Run>("/runs", payload),
  executeRun: (runId: string, payload?: { auto_continue?: boolean; resume_from_step?: string }) =>
    post<Run>(`/runs/${runId}/execute`, payload ?? {}),
  getRun: (runId: string) => get<Run>(`/runs/${runId}`),
  listRunEvents: (runId: string) => get<RunEvent[]>(`/runs/${runId}/events?limit=200`),
  listArtifacts: (runId: string) => get<Artifact[]>(`/runs/${runId}/artifacts?limit=100`)
};
