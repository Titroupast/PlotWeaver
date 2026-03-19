import Link from "next/link";

import { MemorySummaryPanel } from "@/components/memory-summary-panel";
import { serverApi } from "@/lib/api/server";
import type { MemorySnapshotItem } from "@/lib/api/types";

type Props = {
  params: Promise<{ projectId: string }>;
};

export const dynamic = "force-dynamic";

const MEMORY_LABELS: Record<string, string> = {
  CHARACTERS: "人物关系",
  WORLD_RULES: "世界规则",
  STORY_SO_FAR: "前情提要"
};

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
        <p className="muted">优先展示语义化记忆视图。需要排查时，可展开原始 JSON。</p>
      </section>

      <MemorySummaryPanel projectId={projectId} />

      <section className="card stack">
        <h3>当前三层主记忆</h3>
        {snapshots.snapshots.length === 0 ? (
          <p className="muted">暂无主记忆，请先完成至少一次总结重建。</p>
        ) : (
          <div className="memory-grid">
            {snapshots.snapshots.map((item) => (
              <MemorySnapshotCard item={item} key={`${item.memory_type}-${item.version_no}`} />
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
            {history.slice(0, 80).map((item) => (
              <article className="timeline-item" key={item.id}>
                <div className="step-row">
                  <strong>{MEMORY_LABELS[item.memory_type] ?? item.memory_type}</strong>
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

function MemorySnapshotCard({ item }: { item: MemorySnapshotItem }) {
  const label = MEMORY_LABELS[item.memory_type] ?? item.memory_type;
  const payload = item.summary_json;
  const values = summarizeMemory(item.memory_type, payload);
  return (
    <article className="memory-card">
      <div className="step-row">
        <strong>{label}</strong>
        <span className="pill">v{item.version_no}</span>
        <span className="muted">{formatTimestamp(item.updated_at)}</span>
      </div>
      {values.length === 0 ? (
        <p className="muted">暂无内容</p>
      ) : (
        <ul className="memory-list">
          {values.map((line, idx) => (
            <li key={`${item.memory_type}-${idx}`}>{line}</li>
          ))}
        </ul>
      )}
      <details>
        <summary>查看原始 JSON</summary>
        <pre>{JSON.stringify(payload, null, 2)}</pre>
      </details>
    </article>
  );
}

function summarizeMemory(memoryType: string, payload: unknown): string[] {
  if (!payload || typeof payload !== "object") return [];
  const record = payload as Record<string, unknown>;
  if (memoryType === "CHARACTERS" && Array.isArray(record.characters)) {
    return record.characters
      .map((item) => {
        if (typeof item === "string") return item;
        if (!item || typeof item !== "object") return "";
        const character = item as Record<string, unknown>;
        const name = String(character.display_name || character.canonical_name || "").trim();
        const role = String(character.role || "").trim();
        const rels = Array.isArray(character.relationships) ? character.relationships.filter((x) => typeof x === "string") : [];
        const pieces = [name, role ? `（${role}）` : "", rels.length > 0 ? `关系：${rels.slice(0, 2).join("；")}` : ""].filter(Boolean);
        return pieces.join(" ");
      })
      .filter(Boolean);
  }
  if (memoryType === "WORLD_RULES" && Array.isArray(record.rules)) {
    return record.rules.filter((line): line is string => typeof line === "string");
  }
  if (memoryType === "STORY_SO_FAR" && Array.isArray(record.milestones)) {
    return record.milestones.filter((line): line is string => typeof line === "string");
  }
  return [];
}
