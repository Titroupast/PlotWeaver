import Link from "next/link";

import { MemorySummaryPanel } from "@/components/memory-summary-panel";
import { serverApi } from "@/lib/api/server";

type Props = {
  params: Promise<{ projectId: string }>;
};

export const dynamic = "force-dynamic";

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toISOString().replace("T", " ").replace("Z", " UTC");
}

export default async function ProjectMemorySummaryPage({ params }: Props) {
  const { projectId } = await params;
  const [snapshots, history] = await Promise.all([
    serverApi.getMemorySnapshots(projectId).catch(() => ({ project_id: projectId, snapshots: [] })),
    serverApi.listMemoryHistory(projectId).catch(() => [])
  ]);

  return (
    <div className="container stack">
      <section className="card stack">
        <div className="step-row">
          <h1>记忆总结</h1>
          <Link className="button-link secondary" href={`/app/projects/${projectId}`}>
            返回项目
          </Link>
          <Link className="button-link secondary" href={`/app/projects/${projectId}/memory`}>
            记忆审查
          </Link>
        </div>
        <p className="muted">先展示当前已生效记忆，再按需手动触发重建任务。</p>
      </section>

      <MemorySummaryPanel projectId={projectId} />

      <section className="card stack">
        <h3>当前三层主记忆</h3>
        {snapshots.snapshots.length === 0 ? (
          <p className="muted">暂无主记忆，请先完成至少一次总结重建。</p>
        ) : (
          <div className="timeline">
            {snapshots.snapshots.map((item) => (
              <article className="timeline-item" key={`${item.memory_type}-${item.version_no}`}>
                <div className="step-row">
                  <strong>{item.memory_type}</strong>
                  <span className="pill">v{item.version_no}</span>
                  <span className="muted">{formatTimestamp(item.updated_at)}</span>
                </div>
                <pre>{JSON.stringify(item.summary_json, null, 2)}</pre>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="card stack">
        <h3>记忆历史版本</h3>
        {history.length === 0 ? (
          <p className="muted">暂无历史记录。</p>
        ) : (
          <div className="timeline">
            {history.slice(0, 50).map((item) => (
              <article className="timeline-item" key={item.id}>
                <div className="step-row">
                  <strong>{item.memory_type}</strong>
                  <span className="pill">v{item.version_no}</span>
                  <span className="muted">{formatTimestamp(item.updated_at)}</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
