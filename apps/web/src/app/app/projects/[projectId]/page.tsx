import Link from "next/link";
import { notFound } from "next/navigation";

import { ChapterVersionPanel } from "@/components/chapter-version-panel";
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
        <p className="muted">{project.description ?? "暂无简介"}</p>
      </section>

      <section className="card stack">
        <div className="step-row">
          <h3>项目操作</h3>
          <Link className="button-link secondary" href={`/app/projects/${projectId}/memory`}>
            记忆审查
          </Link>
          <Link className="button-link secondary" href={`/app/projects/${projectId}/memory/summary`}>
            记忆总结
          </Link>
        </div>
        <p className="muted">记忆审查负责增量合并；记忆总结为独立任务，按需手动重建。</p>
      </section>

      <section className="grid">
        {chapters.map((chapter) => (
          <article className="card stack" key={chapter.id}>
            <ChapterVersionPanel
              projectId={projectId}
              chapterId={chapter.id}
              chapterTitle={chapter.title}
              chapterStatus={chapter.status}
              chapterSummary={chapter.summary || "暂无摘要"}
            />
            <div className="step-row">
              <span className="muted">章节序号: {chapter.order_index}</span>
              <Link className="button-link" href={`/app/projects/${projectId}/chapters/${chapter.id}/configure`}>
                进入续写配置
              </Link>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
