import Link from "next/link";

import { MemoryReviewPanel } from "@/components/memory-review-panel";
import { serverApi } from "@/lib/api/server";

type Props = {
  params: Promise<{ projectId: string }>;
};

export const dynamic = "force-dynamic";

export default async function ProjectMemoryReviewPage({ params }: Props) {
  const { projectId } = await params;
  const pendingDeltas = await serverApi.listMemoryDeltas(projectId, "PENDING_REVIEW").catch(() => []);

  return (
    <div className="container stack">
      <section className="card stack">
        <div className="step-row">
          <h1>记忆审查</h1>
          <Link className="button-link secondary" href={`/app/projects/${projectId}`}>
            返回项目
          </Link>
          <Link className="button-link secondary" href={`/app/projects/${projectId}/memory/summary`}>
            记忆总结
          </Link>
        </div>
        <p className="muted">本页仅处理 memory delta 的人工审核（合并/拒绝），不自动重建总结。</p>
      </section>

      <MemoryReviewPanel projectId={projectId} initialDeltas={pendingDeltas} />
    </div>
  );
}
