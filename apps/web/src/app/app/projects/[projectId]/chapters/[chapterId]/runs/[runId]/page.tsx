import Link from "next/link";

import { RunLivePanel } from "@/components/run-live-panel";
import { serverApi } from "@/lib/api/server";

type Props = {
  params: Promise<{ projectId: string; chapterId: string; runId: string }>;
};

export const dynamic = "force-dynamic";

export default async function RunProcessPage({ params }: Props) {
  const { projectId, chapterId, runId } = await params;
  const [run, events] = await Promise.all([serverApi.getRun(runId), serverApi.listRunEvents(runId)]);

  return (
    <div className="container">
      <section className="card stack">
        <h1>生成过程</h1>
        <p className="muted">Run ID: {runId}</p>
        <div className="step-row">
          <Link href={`/app/projects/${projectId}/chapters/${chapterId}/runs/${runId}/review`}>
            <button className="secondary">Go To Review</button>
          </Link>
        </div>
      </section>
      <RunLivePanel runId={runId} initialRun={run} initialEvents={events} />
    </div>
  );
}
