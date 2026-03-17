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
        setError(mapApiErrorMessage(err, "Failed to create project"));
      }
    });
  };

  return (
    <form className="stack" onSubmit={onSubmit}>
      <div>
        <label htmlFor="projectTitle">Project Title</label>
        <input
          id="projectTitle"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="输入项目标题"
          required
        />
      </div>
      <div>
        <label htmlFor="projectDesc">Description</label>
        <textarea
          id="projectDesc"
          rows={3}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="可选：项目简介"
        />
      </div>
      <div className="step-row">
        <button type="submit" disabled={pending || !title.trim()}>
          {pending ? "Creating..." : "Create Project"}
        </button>
      </div>
      {error ? <p className="status-danger">{error}</p> : null}
    </form>
  );
}