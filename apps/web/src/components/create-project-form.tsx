"use client";

import { type FormEvent, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";

export function CreateProjectForm() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    startTransition(async () => {
      setError(null);
      try {
        await clientApi.createProject({
          title: title.trim(),
          description: description.trim() || undefined
        });
        setTitle("");
        setDescription("");
        router.refresh();
      } catch (err) {
        setError(mapApiErrorMessage(err, "创建项目失败"));
      }
    });
  };

  return (
    <form className="stack" onSubmit={onSubmit}>
      <div>
        <label htmlFor="projectTitle">项目标题</label>
        <input
          id="projectTitle"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="请输入项目标题"
          required
        />
      </div>
      <div>
        <label htmlFor="projectDesc">项目简介</label>
        <textarea
          id="projectDesc"
          rows={3}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="可选：项目背景或风格"
        />
      </div>
      <div className="step-row">
        <button type="submit" className="action-merge" disabled={pending || !title.trim()}>
          <span className="btn-text">{pending ? "创建中..." : "创建项目"}</span>
        </button>
      </div>
      {error ? <p className="status-danger">{error}</p> : null}
    </form>
  );
}
