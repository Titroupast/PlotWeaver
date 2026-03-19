"use client";

import { useMemo, useState, useTransition } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";
import type { ChapterLatestContent } from "@/lib/api/types";

type Props = {
  projectId: string;
  chapterId: string;
  value: ChapterLatestContent;
  onSaved?: (next: ChapterLatestContent) => void;
};

export function MarkdownContentEditor({ projectId, chapterId, value, onSaved }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value.content);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const wordCount = useMemo(() => draft.trim().length, [draft]);

  const onSave = () => {
    startTransition(async () => {
      setError(null);
      try {
        const saved = await clientApi.updateChapterContent(projectId, chapterId, draft, value.version_no);
        setEditing(false);
        onSaved?.(saved);
      } catch (e) {
        setError(mapApiErrorMessage(e, "正文保存失败"));
      }
    });
  };

  return (
    <section className="content-article">
      <div className="step-row">
        <strong>正文内容</strong>
        <span className="pill">v{value.version_no}</span>
        <span className="muted">{wordCount} 字</span>
      </div>

      {editing ? (
        <div className="stack">
          <textarea
            className="markdown-input"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            rows={18}
          />
          <div className="step-row">
            <button type="button" className="action-merge" onClick={onSave} disabled={pending}>
              <span className="btn-text">{pending ? "保存中..." : "保存覆盖当前版本"}</span>
            </button>
            <button
              type="button"
              className="action-reject"
              disabled={pending}
              onClick={() => {
                setDraft(value.content);
                setEditing(false);
              }}
            >
              <span className="btn-text">取消</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="stack">
          <div className="md-render">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{value.content}</ReactMarkdown>
          </div>
          <div className="step-row">
            <button type="button" className="action-merge" onClick={() => setEditing(true)}>
              <span className="btn-text">编辑正文</span>
            </button>
          </div>
        </div>
      )}
      {error ? <p className="status-danger">{error}</p> : null}
    </section>
  );
}
