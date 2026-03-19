import Link from "next/link";

export default function NotFoundPage() {
  return (
    <div className="container">
      <section className="card stack">
        <h1>Not Found</h1>
        <p className="muted">The page you requested does not exist.</p>
        <div>
          <Link className="button-link" href="/app/projects">
            Back to Projects
          </Link>
        </div>
      </section>
    </div>
  );
}
