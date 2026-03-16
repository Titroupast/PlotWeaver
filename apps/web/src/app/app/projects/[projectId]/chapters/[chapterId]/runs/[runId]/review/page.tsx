import Link from "next/link";

import { ArtifactReview } from "@/components/artifact-review";
import { ReviewDecisionPanel } from "@/components/review-decision-panel";
import { serverApi } from "@/lib/api/server";

type Props = {
  params: Promise<{ projectId: string; chapterId: string; runId: string }>;
};

export const dynamic = "force-dynamic";

export default async function ReviewPage({ params }: Props) {
  const { projectId, chapterId, runId } = await params;
  const [run, artifacts] = await Promise.all([serverApi.getRun(runId), serverApi.listArtifacts(runId)]);

  return (
    <div className="container">
      <section className="card stack">
        <h1>结果审阅</h1>
        <p className="muted">Run state: {run.state}</p>
        <div className="step-row">
          <Link href={`/app/projects/${projectId}/chapters/${chapterId}/runs/${runId}`}>
            <button className="secondary">Back To Process</button>
          </Link>
        </div>
      </section>
      <ReviewDecisionPanel runId={runId} runState={run.state} />
      {artifacts.length === 0 ? (
        <section className="card">No artifacts yet. Return to process page and execute run.</section>
      ) : (
        <ArtifactReview artifacts={artifacts} />
      )}
    </div>
  );
}
