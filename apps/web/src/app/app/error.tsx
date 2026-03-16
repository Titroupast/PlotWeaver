"use client";

export default function AppError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="container">
      <div className="card stack">
        <h2>Something went wrong</h2>
        <p className="status-danger">{error.message}</p>
        <div>
          <button onClick={reset}>Retry</button>
        </div>
      </div>
    </div>
  );
}
