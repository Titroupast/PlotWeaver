"use client";

import { useTransition, useState } from "react";
import { useRouter } from "next/navigation";

import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";

export function ProjectDeleteButton({ projectId }: { projectId: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const onDelete = () => {
    const yes = window.confirm("确认删除该项目？此操作会隐藏项目并不可恢复。");
    if (!yes) return;
    startTransition(async () => {
      setError(null);
      try {
        await clientApi.deleteProject(projectId);
        router.refresh();
      } catch (e) {
        setError(mapApiErrorMessage(e, "删除项目失败"));
      }
    });
  };

  return (
    <div className="stack">
      <button className="action-reject" type="button" onClick={onDelete} disabled={pending}>
        <span>{pending ? "删除中..." : "删除项目"}</span>
      </button>
      {error ? <p className="status-danger">{error}</p> : null}
    </div>
  );
}
