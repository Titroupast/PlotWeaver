import Link from "next/link";
import { notFound } from "next/navigation";

import { serverApi } from "@/lib/api/server";

type Props = {
  params: Promise<{ projectId: string }>;
};

export const dynamic = "force-dynamic";

export default async function ProjectDetailPage({ params }: Props) {
  const { projectId } = await params;
  const [project, chapters] = await Promise.all([
    serverApi.getProject(projectId).catch(() => null),
    serverApi.listChapters(projectId)
  ]);

  if (!project) {
    notFound();
  }

  return (
    <div className="container">
      <section className="card stack">
        <h1>{project.title}</h1>
        <p className="muted">{project.description ?? "No description"}</p>
      </section>
      <section className="grid">
        {chapters.map((chapter) => (
          <article className="card stack" key={chapter.id}>
            <div className="step-row">
              <h3>{chapter.title}</h3>
              <span className="pill">{chapter.status}</span>
            </div>
            <p className="muted">{chapter.summary || "No summary"}</p>
            <div className="step-row">
              <span className="muted">order: {chapter.order_index}</span>
              <Link href={`/app/projects/${projectId}/chapters/${chapter.id}/configure`}>
                <button>Configure Continuation</button>
              </Link>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
