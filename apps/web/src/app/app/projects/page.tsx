import Link from "next/link";

import { CreateProjectForm } from "@/components/create-project-form";
import { serverApi } from "@/lib/api/server";

export const dynamic = "force-dynamic";

export default async function ProjectsPage() {
  const projects = await serverApi.listProjects();

  return (
    <div className="container">
      <section className="card stack">
        <h1>项目管理</h1>
        <p className="muted">管理小说项目并进入章节续写流程。</p>
      </section>

      <section className="card stack">
        <h3>创建项目</h3>
        <CreateProjectForm />
      </section>

      <section className="grid">
        {projects.length === 0 ? (
          <article className="card">暂无项目，请先创建项目。</article>
        ) : (
          projects.map((project) => (
            <article className="card stack" key={project.id}>
              <div className="step-row">
                <h3>{project.title}</h3>
                <span className="pill">{project.status}</span>
              </div>
              <p className="muted">{project.description ?? "暂无简介"}</p>
              <div className="step-row">
                <span className="muted">语言: {project.language}</span>
                <Link href={`/app/projects/${project.id}`}>
                  <button>进入项目</button>
                </Link>
              </div>
            </article>
          ))
        )}
      </section>
    </div>
  );
}