"use client";

import { useEffect, useMemo, useState, useTransition } from "react";

import { clientApi } from "@/lib/api/client";
import { MarkdownContentEditor } from "@/components/markdown-content-editor";
import type { ChapterLatestContent, ChapterVersion } from "@/lib/api/types";

type ChapterVersionPanelProps = {
  projectId: string;
  chapterId: string;
  chapterSummary: string;
  chapterTitle: string;
  chapterStatus: string;
};

export function ChapterVersionPanel({
  projectId,
  chapterId,
  chapterSummary,
  chapterTitle,
  chapterStatus
}: ChapterVersionPanelProps) {
  const [versions, setVersions] = useState<ChapterVersion[]>([]);
  const [content, setContent] = useState<ChapterLatestContent | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<number | "">("");
  const [selectedTitle, setSelectedTitle] = useState<string>(chapterTitle);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    let alive = true;
    startTransition(async () => {
      try {
        setError(null);
        const list = await clientApi.listChapterVersions(projectId, chapterId);
        if (!alive) return;
        setVersions(list);
        if (list.length === 0) {
          setContent(null);
          setSelectedVersion("");
          setSelectedTitle(chapterTitle);
          return;
        }
        const latest = list[0];
        setSelectedVersion(latest.version_no);
        setSelectedTitle(latest.version_title || chapterTitle);
        const payload = await clientApi.getChapterContent(projectId, chapterId, latest.version_no);
        if (!alive) return;
        setContent(payload);
      } catch {
        if (!alive) return;
        setError("加载章节版本失败");
      }
    });
    return () => {
      alive = false;
    };
  }, [projectId, chapterId, chapterTitle]);

  const options = useMemo(
    () =>
      versions.map((item) => ({
        value: item.version_no,
        label: `v${item.version_no} · ${item.version_title || chapterTitle}`
      })),
    [versions, chapterTitle]
  );

  const onVersionChange = (value: string) => {
    const versionNo = Number(value);
    if (!Number.isFinite(versionNo) || versionNo <= 0) return;
    setSelectedVersion(versionNo);

    const found = versions.find((item) => item.version_no === versionNo);
    setSelectedTitle(found?.version_title || chapterTitle);

    startTransition(async () => {
      try {
        setError(null);
        const payload = await clientApi.getChapterContent(projectId, chapterId, versionNo);
        setContent(payload);
      } catch {
        setError(`加载 v${versionNo} 失败`);
      }
    });
  };

  return (
    <div className="stack">
      <div className="step-row chapter-heading">
        <h3>{selectedTitle || chapterTitle}</h3>
        <span className="pill">{chapterStatus}</span>
      </div>

      <div className="step-row">
        <label htmlFor={`version-${chapterId}`}>正文版本</label>
        <select
          id={`version-${chapterId}`}
          value={selectedVersion}
          onChange={(event) => onVersionChange(event.target.value)}
          disabled={pending || versions.length === 0}
        >
          {versions.length === 0 ? <option value="">暂无版本</option> : null}
          {options.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      </div>

      {selectedVersion ? <p className="muted">当前查看：v{selectedVersion} · 标题：{selectedTitle}</p> : null}
      {error ? <p className="status-danger">{error}</p> : null}

      {content ? (
        <div className="stack">
          <p className="muted">
            版本时间：{new Date(content.created_at).toLocaleString("zh-CN")} · {content.byte_size} bytes
          </p>
          <MarkdownContentEditor
            projectId={projectId}
            chapterId={chapterId}
            value={content}
            onSaved={(next) => setContent(next)}
          />
        </div>
      ) : (
        <p className="muted">{chapterSummary || "暂无正文版本，请先运行续写。"}</p>
      )}
    </div>
  );
}
