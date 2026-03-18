import type { Artifact } from "@/lib/api/types";

type ArtifactReviewProps = {
  artifacts: Artifact[];
};

const ORDER = ["OUTLINE", "REVIEW", "CHARACTERS", "CHAPTER_META", "MEMORY_GATE"];

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toISOString().replace("T", " ").replace("Z", " UTC");
}

export function ArtifactReview({ artifacts }: ArtifactReviewProps) {
  const sorted = [...artifacts].sort((a, b) => ORDER.indexOf(a.artifact_type) - ORDER.indexOf(b.artifact_type));

  return (
    <div className="stack">
      {sorted.map((artifact) => (
        <article className="card stack" key={artifact.id}>
          <div className="step-row">
            <h3>{artifact.artifact_type}</h3>
            <span className="muted">v{artifact.version_no}</span>
            <span className="muted">{formatTimestamp(artifact.created_at)}</span>
          </div>
          <pre>{JSON.stringify(artifact.payload_json, null, 2)}</pre>
        </article>
      ))}
    </div>
  );
}
