import Link from "next/link";
import { notFound } from "next/navigation";

import { RunLivePanel, type AgentStep } from "@/components/run-live-panel";
import { serverApi } from "@/lib/api/server";
import type { RunEvent } from "@/lib/api/types";

type Props = {
  params: Promise<{ projectId: string; chapterId: string; runId: string; agent: string }>;
};

export const dynamic = "force-dynamic";

const AGENT_ROUTE_TO_STEP: Record<string, AgentStep> = {
  planner: "PLANNER",
  writer: "WRITER",
  reviewer: "REVIEWER",
  "memory-curator": "MEMORY_CURATOR"
};

const AGENT_STEP_TO_LABEL: Record<AgentStep, string> = {
  PLANNER: "规划师（Planner）",
  WRITER: "作家（Writer）",
  REVIEWER: "审阅员（Reviewer）",
  MEMORY_CURATOR: "记忆管理员（Memory Curator）"
};

const STEP_PROMPTS: Record<AgentStep, string[]> = {
  PLANNER: ["planner_system.txt", "planner_user.txt"],
  WRITER: ["writer_system.txt", "writer_user.txt"],
  REVIEWER: ["reviewer_system.txt", "reviewer_user.txt"],
  MEMORY_CURATOR: ["memory_curator_system.txt", "memory_curator_user.txt"]
};

const STEP_ARTIFACT_TYPES: Record<AgentStep, string[]> = {
  PLANNER: ["OUTLINE"],
  WRITER: ["CHAPTER_META"],
  REVIEWER: ["REVIEW"],
  MEMORY_CURATOR: ["MEMORY_GATE"]
};

export default async function RunAgentPage({ params }: Props) {
  const { projectId, chapterId, runId, agent } = await params;
  const step = AGENT_ROUTE_TO_STEP[agent];
  if (!step) notFound();

  const [run, events, artifacts] = await Promise.all([
    serverApi.getRun(runId),
    serverApi.listRunEvents(runId),
    serverApi.listArtifacts(runId)
  ]);
  const stepArtifacts = artifacts.filter((item) => STEP_ARTIFACT_TYPES[step].includes(item.artifact_type));
  const latestStepEvent = findLatestStepCompletedEvent(events, step);

  return (
    <div className="container stack">
      <section className="card stack">
        <h1>{AGENT_STEP_TO_LABEL[step]} 独立界面</h1>
        <p className="muted">运行 ID: {runId}</p>
        <div className="step-row">
          <Link
            className="button-link secondary"
            href={`/app/projects/${projectId}/chapters/${chapterId}/runs/${runId}`}
            prefetch={false}
          >
            返回生成总览
          </Link>
          <Link
            className="button-link secondary"
            href={`/app/projects/${projectId}/chapters/${chapterId}/runs/${runId}/agents/planner`}
            prefetch={false}
          >
            Planner
          </Link>
          <Link
            className="button-link secondary"
            href={`/app/projects/${projectId}/chapters/${chapterId}/runs/${runId}/agents/writer`}
            prefetch={false}
          >
            Writer
          </Link>
          <Link
            className="button-link secondary"
            href={`/app/projects/${projectId}/chapters/${chapterId}/runs/${runId}/agents/reviewer`}
            prefetch={false}
          >
            Reviewer
          </Link>
          <Link
            className="button-link secondary"
            href={`/app/projects/${projectId}/chapters/${chapterId}/runs/${runId}/agents/memory-curator`}
            prefetch={false}
          >
            Memory Curator
          </Link>
        </div>
      </section>

      <section className="card stack">
        <h3>本智能体提示词文件</h3>
        <p className="muted">后端实际读取目录：`apps/api/src/plotweaver_api/prompts`</p>
        <div className="step-row">
          {STEP_PROMPTS[step].map((name) => (
            <span className="pill" key={name}>
              {name}
            </span>
          ))}
        </div>
      </section>

      <section className="card stack">
        <h3>本智能体最近一次输出</h3>
        {latestStepEvent ? (
          <article className="timeline-item">
            <div className="step-row">
              <strong>{step} 最近执行</strong>
              <span className="muted">{formatTimestamp(latestStepEvent.created_at)}</span>
              <span className="pill">{latestStepEvent.payload_json?.llm_used ? "已调用模型" : "回退默认"}</span>
            </div>
            <pre>{JSON.stringify(latestStepEvent.payload_json ?? {}, null, 2)}</pre>
          </article>
        ) : (
          <p className="muted">暂无该智能体执行记录。</p>
        )}
      </section>

      <section className="card stack">
        <h3>本智能体结构化产物</h3>
        {stepArtifacts.length === 0 ? (
          <p className="muted">暂无产物。</p>
        ) : (
          <div className="timeline">
            {stepArtifacts.map((artifact) => (
              <article key={artifact.id} className="timeline-item">
                <div className="step-row">
                  <strong>{artifact.artifact_type}</strong>
                  <span className="pill">v{artifact.version_no}</span>
                </div>
                <pre>{JSON.stringify(artifact.payload_json, null, 2)}</pre>
              </article>
            ))}
          </div>
        )}
      </section>

      <RunLivePanel runId={runId} initialRun={run} initialEvents={events} fixedStep={step} />
    </div>
  );
}

function findLatestStepCompletedEvent(events: RunEvent[], step: AgentStep): RunEvent | null {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    if (events[i].event_type === "STEP_COMPLETED" && events[i].step === step) {
      return events[i];
    }
  }
  return null;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toISOString().replace("T", " ").replace("Z", " UTC");
}
