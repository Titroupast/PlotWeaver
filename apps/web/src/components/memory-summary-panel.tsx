"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";
import type { MemoryRebuildResponse } from "@/lib/api/types";

type Props = {
  projectId: string;
};

export function MemorySummaryPanel({ projectId }: Props) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<MemoryRebuildResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onRebuild = () => {
    startTransition(async () => {
      setError(null);
      try {
        const resp = await clientApi.rebuildMemorySummary(projectId);
        setResult(resp);
        router.refresh();
      } catch (e) {
        setError(mapApiErrorMessage(e, "重建记忆总结失败"));
      }
    });
  };

  return (
    <section className="card stack">
      <div className="step-row">
        <h3>记忆总结任务</h3>
        <button className="action-merge" disabled={pending} onClick={onRebuild}>
          <span>{pending ? "重建中..." : "重建总结"}</span>
        </button>
      </div>
      <p className="muted">该操作会基于当前项目全部章节正文，重建人物关系、世界规则、剧情摘要三层主记忆。</p>
      {result ? (
        <div className="stack">
          <p className="status-ok">
            完成：章节 {result.chapter_count}，更新类型 {result.updated_types.length === 0 ? "无" : result.updated_types.join(", ")}
          </p>
          <p className="muted">
            来源：CHARACTERS={result.sources?.CHARACTERS ?? "UNKNOWN"}，WORLD_RULES={result.sources?.WORLD_RULES ?? "UNKNOWN"}，STORY_SO_FAR={result.sources?.STORY_SO_FAR ?? "UNKNOWN"}
          </p>
          <p className="muted">
            原因：CHARACTERS={result.reasons?.CHARACTERS ?? "-"}，WORLD_RULES={result.reasons?.WORLD_RULES ?? "-"}，STORY_SO_FAR={result.reasons?.STORY_SO_FAR ?? "-"}
          </p>
        </div>
      ) : null}
      {error ? <p className="status-danger">{error}</p> : null}
    </section>
  );
}
