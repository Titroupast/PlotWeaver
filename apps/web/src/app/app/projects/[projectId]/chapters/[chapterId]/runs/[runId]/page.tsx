import Link from "next/link";

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
      <section className="card stack">
        <h1>生成过程</h1>
        <p className="muted">运行 ID: {runId}</p>
        <div className="step-row">
          <Link href={`/app/projects/${projectId}/chapters/${chapterId}/runs/${runId}/review`}>
            <button className="secondary">查看审阅页</button>
          </Link>
        </div>
      </section>

      {latestContent ? (
        <section className="card stack">
          <div className="step-row">
            <h3>最新正文</h3>
            <span className="pill">v{latestContent.version_no}</span>
          </div>
          <p className="muted">
            {latestContent.storage_bucket} / {latestContent.storage_key}
          </p>
          <pre>{latestContent.content}</pre>
        </section>
      ) : null}

      <RunLivePanel runId={runId} initialRun={run} initialEvents={events} />
    </div>
  );
}