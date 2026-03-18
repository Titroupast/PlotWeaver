import Link from "next/link";

import { MemoryReviewPanel } from "@/components/memory-review-panel";
import { serverApi } from "@/lib/api/server";

type Props = {
  params: Promise<{ projectId: string }>;
};

export const dynamic = "force-dynamic";

export default async function ProjectMemoryPage({ params }: Props) {
  const { projectId } = await params;
  const [snapshots, pendingDeltas, history] = await Promise.all([
    serverApi.getMemorySnapshots(projectId).catch(() => ({ project_id: projectId, snapshots: [] })),
    serverApi.listMemoryDeltas(projectId, "PENDING_REVIEW").catch(() => []),
    serverApi.listMemoryHistory(projectId).catch(() => [])
  ]);

  return (
    <div className="container stack">
      <section className="card stack">
        <div className="step-row">
          <h1>记忆管理</h1>
          <Link href={`/app/projects/${projectId}`}>
            <button className="secondary">返回项目</button>
          </Link>
        </div>
        <p className="muted">主记忆标准来源为 memories.summary_json，本页用于人工确认高风险增量。</p>
      </section>

      <section className="card stack">
        <h3>三层主记忆快照</h3>
        {snapshots.snapshots.length === 0 ? (
          <p className="muted">暂无主记忆快照。</p>
        ) : (
          <div className="timeline">
            {snapshots.snapshots.map((item) => (
              <article className="timeline-item" key={`${item.memory_type}-${item.version_no}`}>
                <div className="step-row">
                  <strong>{item.memory_type}</strong>
                  <span className="pill">v{item.version_no}</span>
                </div>
                <pre>{JSON.stringify(item.summary_json, null, 2)}</pre>
              </article>
            ))}
          </div>
        )}
      </section>

      <MemoryReviewPanel projectId={projectId} initialDeltas={pendingDeltas} />

      <section className="card stack">
        <h3>主记忆历史（简版）</h3>
        {history.length === 0 ? (
          <p className="muted">暂无历史记录。</p>
        ) : (
          <div className="timeline">
            {history.slice(0, 30).map((item) => (
              <article className="timeline-item" key={item.id}>
                <div className="step-row">
                  <strong>{item.memory_type}</strong>
                  <span className="pill">v{item.version_no}</span>
                  <span className="muted">{new Date(item.updated_at).toLocaleString()}</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
