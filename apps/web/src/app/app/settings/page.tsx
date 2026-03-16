export default function SettingsPage() {
  return (
    <div className="container">
      <section className="card stack">
        <h1>Settings</h1>
        <p className="muted">
          API Base URL: <code>{process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"}</code>
        </p>
        <p className="muted">
          Tenant ID: <code>{process.env.NEXT_PUBLIC_TENANT_ID ?? "00000000-0000-0000-0000-000000000001"}</code>
        </p>
      </section>
    </div>
  );
}
