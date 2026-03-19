"use client";

import { useMemo, useState, useTransition } from "react";

import { JsonValueEditor } from "@/components/json-value-editor";
import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";
import type { Artifact } from "@/lib/api/types";

type ArtifactReviewProps = {
  runId: string;
  artifacts: Artifact[];
};

const ORDER = ["OUTLINE", "REVIEW", "CHARACTERS", "CHAPTER_META", "MEMORY_GATE"];
const LABELS: Record<string, string> = {
  OUTLINE: "大纲",
  REVIEW: "审阅",
  CHARACTERS: "人物关系",
  CHAPTER_META: "章节元信息",
  MEMORY_GATE: "记忆闸门"
};

export function ArtifactReview({ runId, artifacts }: ArtifactReviewProps) {
  const sorted = useMemo(
    () => [...artifacts].sort((a, b) => ORDER.indexOf(a.artifact_type) - ORDER.indexOf(b.artifact_type)),
    [artifacts]
  );
  const [working, setWorking] = useState<Record<string, Record<string, unknown>>>(
    Object.fromEntries(sorted.map((item) => [item.id, item.payload_json]))
  );
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const onSave = (artifact: Artifact) => {
    const payload = working[artifact.id] ?? artifact.payload_json;
    startTransition(async () => {
      setError(null);
      try {
        const saved = await clientApi.updateArtifactPayload(runId, artifact.id, payload);
        setWorking((prev) => ({ ...prev, [artifact.id]: saved.payload_json }));
        setEditingId(null);
      } catch (e) {
        setError(mapApiErrorMessage(e, "结构化产物保存失败"));
      }
    });
  };

  return (
    <div className="stack">
      {sorted.map((artifact) => {
        const isEditing = editingId === artifact.id;
        return (
          <article className="card stack artifact-card" key={artifact.id}>
            <div className="step-row">
              <h3>{LABELS[artifact.artifact_type] ?? artifact.artifact_type}</h3>
              <span className="pill">{artifact.artifact_type}</span>
              <span className="muted">v{artifact.version_no}</span>
              <span className="muted">{formatTimestamp(artifact.created_at)}</span>
            </div>

            {isEditing ? (
              <JsonValueEditor
                value={working[artifact.id] ?? artifact.payload_json}
                onChange={(next) =>
                  setWorking((prev) => ({ ...prev, [artifact.id]: next as Record<string, unknown> }))
                }
                disabled={pending}
              />
            ) : (
              <pre>{JSON.stringify(working[artifact.id] ?? artifact.payload_json, null, 2)}</pre>
            )}

            <div className="step-row">
              {isEditing ? (
                <>
                  <button type="button" className="action-merge" disabled={pending} onClick={() => onSave(artifact)}>
                    <span className="btn-text">{pending ? "保存中..." : "保存内容（结构锁定）"}</span>
                  </button>
                  <button
                    type="button"
                    className="action-reject"
                    disabled={pending}
                    onClick={() => {
                      setWorking((prev) => ({ ...prev, [artifact.id]: artifact.payload_json }));
                      setEditingId(null);
                    }}
                  >
                    <span className="btn-text">取消</span>
                  </button>
                </>
              ) : (
                <button type="button" className="action-merge" onClick={() => setEditingId(artifact.id)}>
                  <span className="btn-text">编辑内容</span>
                </button>
              )}
            </div>
          </article>
        );
      })}
      {error ? <p className="status-danger">{error}</p> : null}
    </div>
  );
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toISOString().replace("T", " ").replace("Z", " UTC");
}
