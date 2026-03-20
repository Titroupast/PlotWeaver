"use client";

import { useEffect, useMemo, useState, useTransition } from "react";

import { JsonValueEditor } from "@/components/json-value-editor";
import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";
import type { Artifact } from "@/lib/api/types";

type ArtifactReviewProps = {
  runId: string;
  artifacts: Artifact[];
};

const ORDER = ["OUTLINE", "CHAPTER_META", "REVIEW", "MEMORY_GATE", "CHARACTERS"];
const LABELS: Record<string, string> = {
  OUTLINE: "大纲",
  REVIEW: "审阅报告",
  CHARACTERS: "人物关系",
  CHAPTER_META: "章节元信息",
  MEMORY_GATE: "记忆闸门"
};

export function ArtifactReview({ runId, artifacts }: ArtifactReviewProps) {
  const sorted = useMemo(
    () => [...artifacts].sort((a, b) => ORDER.indexOf(a.artifact_type) - ORDER.indexOf(b.artifact_type)),
    [artifacts]
  );
  const tabs = useMemo(() => sorted.map((item) => item.artifact_type), [sorted]);
  const [activeType, setActiveType] = useState<string>(tabs[0] ?? "");
  const [working, setWorking] = useState<Record<string, Record<string, unknown>>>(
    Object.fromEntries(sorted.map((item) => [item.id, item.payload_json]))
  );
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    if (tabs.length > 0 && !tabs.includes(activeType)) setActiveType(tabs[0]);
  }, [tabs, activeType]);

  const current = sorted.find((item) => item.artifact_type === activeType) ?? sorted[0];
  if (!current) {
    return <p className="muted">暂无产物。</p>;
  }
  const isEditing = editingId === current.id;

  const onSave = () => {
    const payload = working[current.id] ?? current.payload_json;
    startTransition(async () => {
      setError(null);
      try {
        const saved = await clientApi.updateArtifactPayload(runId, current.id, payload);
        setWorking((prev) => ({ ...prev, [current.id]: saved.payload_json }));
        setEditingId(null);
      } catch (e) {
        setError(mapApiErrorMessage(e, "结构化产物保存失败"));
      }
    });
  };

  return (
    <div className="stack">
      <div className="tab-row" role="tablist" aria-label="产物分类">
        {tabs.map((type) => (
          <button
            key={type}
            type="button"
            className={`tab-button ${type === activeType ? "active" : ""}`}
            onClick={() => {
              setActiveType(type);
              setEditingId(null);
            }}
          >
            <span className="btn-text">{LABELS[type] ?? type}</span>
          </button>
        ))}
      </div>

      <article className="card stack artifact-card">
        <div className="step-row">
          <h3>{LABELS[current.artifact_type] ?? current.artifact_type}</h3>
          <span className="pill">{current.artifact_type}</span>
          <span className="muted">v{current.version_no}</span>
          <span className="muted">{formatTimestamp(current.created_at)}</span>
        </div>

        {!isEditing ? <ArtifactSemanticView artifact={working[current.id] ?? current.payload_json} type={current.artifact_type} /> : null}
        {isEditing ? (
          <JsonValueEditor
            value={working[current.id] ?? current.payload_json}
            onChange={(next) => setWorking((prev) => ({ ...prev, [current.id]: next as Record<string, unknown> }))}
            disabled={pending}
          />
        ) : null}

        <details>
          <summary>查看原始 JSON</summary>
          <pre>{JSON.stringify(working[current.id] ?? current.payload_json, null, 2)}</pre>
        </details>

        <div className="step-row">
          {isEditing ? (
            <>
              <button type="button" className="action-merge" disabled={pending} onClick={onSave}>
                <span className="btn-text">{pending ? "保存中..." : "保存内容（结构锁定）"}</span>
              </button>
              <button
                type="button"
                className="action-reject"
                disabled={pending}
                onClick={() => {
                  setWorking((prev) => ({ ...prev, [current.id]: current.payload_json }));
                  setEditingId(null);
                }}
              >
                <span className="btn-text">取消</span>
              </button>
            </>
          ) : (
            <button type="button" className="action-merge" onClick={() => setEditingId(current.id)}>
              <span className="btn-text">编辑内容</span>
            </button>
          )}
        </div>
      </article>
      {error ? <p className="status-danger">{error}</p> : null}
    </div>
  );
}

function ArtifactSemanticView({ artifact, type }: { artifact: Record<string, unknown>; type: string }) {
  if (type === "OUTLINE") {
    const beats = Array.isArray(artifact.beats) ? artifact.beats.filter((x): x is string => typeof x === "string") : [];
    const goal = String(artifact.chapter_goal ?? "");
    const conflict = String(artifact.conflict ?? "");
    const hook = String(artifact.ending_hook ?? "");
    return (
      <div className="stack">
        <p><strong>章节目标：</strong>{goal || "未填"}</p>
        <p><strong>核心冲突：</strong>{conflict || "未填"}</p>
        <p><strong>结尾钩子：</strong>{hook || "未填"}</p>
        <div>
          <strong>剧情节拍：</strong>
          <ul className="memory-list">
            {beats.map((beat, idx) => <li key={`beat-${idx}`}>{beat}</li>)}
          </ul>
        </div>
      </div>
    );
  }

  if (type === "CHAPTER_META") {
    return (
      <div className="stack">
        <p><strong>标题：</strong>{String(artifact.title ?? "") || "未填"}</p>
        <p><strong>章节号：</strong>{String(artifact.order_index ?? "") || "未填"}</p>
        <p><strong>摘要：</strong>{String(artifact.summary ?? "") || "未填"}</p>
      </div>
    );
  }

  if (type === "REVIEW") {
    const issues = Array.isArray(artifact.repetition_issues) ? artifact.repetition_issues.filter((x): x is string => typeof x === "string") : [];
    const suggestions = Array.isArray(artifact.revision_suggestions) ? artifact.revision_suggestions.filter((x): x is string => typeof x === "string") : [];
    return (
      <div className="stack">
        <p><strong>风格匹配分：</strong>{String(artifact.style_match_score ?? "-")}</p>
        <p><strong>角色一致性：</strong>{String(artifact.character_consistency_score ?? "-")}</p>
        <p><strong>世界一致性：</strong>{String(artifact.world_consistency_score ?? "-")}</p>
        <div>
          <strong>问题：</strong>
          <ul className="memory-list">
            {issues.slice(0, 5).map((issue, idx) => <li key={`issue-${idx}`}>{issue}</li>)}
          </ul>
        </div>
        <div>
          <strong>建议：</strong>
          <ul className="memory-list">
            {suggestions.slice(0, 5).map((s, idx) => <li key={`sug-${idx}`}>{s}</li>)}
          </ul>
        </div>
      </div>
    );
  }

  if (type === "MEMORY_GATE") {
    const issues = Array.isArray(artifact.issues) ? artifact.issues.filter((x): x is string => typeof x === "string") : [];
    return (
      <div className="stack">
        <p><strong>闸门通过：</strong>{String(artifact.pass ?? "-")}</p>
        <p><strong>建议动作：</strong>{String(artifact.recommended_action ?? "-")}</p>
        <div>
          <strong>风险项：</strong>
          <ul className="memory-list">
            {issues.map((issue, idx) => <li key={`gate-${idx}`}>{issue}</li>)}
          </ul>
        </div>
      </div>
    );
  }

  if (type === "CHARACTERS") {
    const chars = Array.isArray(artifact.characters) ? artifact.characters : [];
    return (
      <div className="stack">
        <p><strong>人物数量：</strong>{chars.length}</p>
      </div>
    );
  }

  return null;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toISOString().replace("T", " ").replace("Z", " UTC");
}
