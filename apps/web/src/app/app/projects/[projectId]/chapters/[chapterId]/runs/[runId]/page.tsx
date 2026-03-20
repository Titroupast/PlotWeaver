import Link from "next/link";

import { MarkdownContentEditor } from "@/components/markdown-content-editor";
import { RunLivePanel } from "@/components/run-live-panel";
import { serverApi } from "@/lib/api/server";

type Props = {
  params: Promise<{ projectId: string; chapterId: string; runId: string }>;
};

export const dynamic = "force-dynamic";

export default async function RunProcessPage({ params }: Props) {
  const { projectId, chapterId, runId } = await params;
  const [run, events, latestContent] = await Promise.all([
    serverApi.getRun(runId),
    serverApi.listRunEvents(runId),
    serverApi.getLatestChapterContent(projectId, chapterId).catch(() => null)
  ]);

  return (
    <div className="container stack">
      <a className="skip-link" href="#run-main-content">
        跳到正文
      </a>
      <section className="card stack">
        <h1>生成过程</h1>
        <p className="muted">运行 ID: {runId}</p>
        <div className="step-row">
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
        <div className="step-row">
          <Link
            className="button-link secondary"
            href={`/app/projects/${projectId}/chapters/${chapterId}/runs/${runId}/review`}
            prefetch={false}
          >
            查看审阅页
          </Link>
          <Link className="button-link secondary" href={`/app/projects/${projectId}/memory`} prefetch={false}>
            记忆审查
          </Link>
          <Link className="button-link secondary" href={`/app/projects/${projectId}/memory/summary`} prefetch={false}>
            记忆总结
          </Link>
        </div>
      </section>

      {latestContent ? (
        <section className="card stack" id="run-main-content">
          <div className="step-row">
            <h3>最新正文</h3>
            <span className="pill">v{latestContent.version_no}</span>
          </div>
          <details>
            <summary>查看存储路径</summary>
            <p className="muted">
              {latestContent.storage_bucket} / {latestContent.storage_key}
            </p>
          </details>
          <MarkdownContentEditor projectId={projectId} chapterId={chapterId} value={latestContent} />
        </section>
      ) : null}

      <RunLivePanel runId={runId} initialRun={run} initialEvents={events} />
    </div>
  );
}
