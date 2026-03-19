"use client";

import { type FormEvent, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";

export function ImportProjectForm() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setError("请选择 .txt 小说文件");
      return;
    }
    startTransition(async () => {
      setError(null);
      setOk(null);
      try {
        const resp = await clientApi.importProjectFromTxt({
          title: title.trim(),
          description: description.trim() || undefined,
          file
        });
        setOk(`导入成功：${resp.project.title}（${resp.chapter_count} 章）`);
        setTitle("");
        setDescription("");
        setFile(null);
        router.refresh();
      } catch (err) {
        setError(mapApiErrorMessage(err, "导入项目失败"));
      }
    });
  };

  return (
    <form className="stack" onSubmit={onSubmit}>
      <div>
        <label htmlFor="importTitle">项目标题</label>
        <input
          id="importTitle"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="请输入导入后的项目标题"
          required
        />
      </div>
      <div>
        <label htmlFor="importDesc">项目简介</label>
        <textarea
          id="importDesc"
          rows={3}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="可选：导入来源说明"
        />
      </div>
      <div>
        <label htmlFor="importFile">小说 txt 文件</label>
        <input
          id="importFile"
          type="file"
          accept=".txt,text/plain"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          required
        />
      </div>
      <div className="step-row">
        <button type="submit" className="action-merge" disabled={pending || !title.trim() || !file}>
          <span className="btn-text">{pending ? "导入中..." : "导入并拆分章节"}</span>
        </button>
      </div>
      {ok ? <p className="status-ok">{ok}</p> : null}
      {error ? <p className="status-danger">{error}</p> : null}
    </form>
  );
}
