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
        <p className="muted">运行状态: {run.state}</p>
        <div className="step-row">
          <Link href={`/app/projects/${projectId}/chapters/${chapterId}/runs/${runId}`}>
            <button className="secondary">返回生成过程</button>
          </Link>
        </div>
      </section>
      <ReviewDecisionPanel runId={runId} runState={run.state} />
      {artifacts.length === 0 ? (
        <section className="card">暂无结构化产物，请先执行步骤。</section>
      ) : (
        <ArtifactReview runId={runId} artifacts={artifacts} />
      )}
    </div>
  );
}
