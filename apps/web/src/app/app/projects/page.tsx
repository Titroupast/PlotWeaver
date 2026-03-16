import Link from "next/link";

import { serverApi } from "@/lib/api/server";

export const dynamic = "force-dynamic";

export default async function ProjectsPage() {
  const projects = await serverApi.listProjects();

  return (
    <div className="container">
      <section className="card stack">
        <h1>Projects</h1>
        <p className="muted">管理小说项目并进入章节续写流程。</p>
      </section>
      <section className="grid">
        {projects.length === 0 ? (
          <article className="card">No project found. Use API to create one first.</article>
        ) : (
          projects.map((project) => (
            <article className="card stack" key={project.id}>
              <div className="step-row">
                <h3>{project.title}</h3>
                <span className="pill">{project.status}</span>
              </div>
              <p className="muted">{project.description ?? "No description"}</p>
              <div className="step-row">
                <span className="muted">language: {project.language}</span>
                <Link href={`/app/projects/${project.id}`}>
                  <button>Open</button>
                </Link>
              </div>
            </article>
          ))
        )}
      </section>
    </div>
  );
}
