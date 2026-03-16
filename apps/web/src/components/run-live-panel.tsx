"use client";

import { useEffect, useMemo, useState, useTransition } from "react";

import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";
import type { Run, RunEvent } from "@/lib/api/types";

const STEPS = ["PLANNER", "WRITER", "REVIEWER", "MEMORY_CURATOR"];
const DONE_STATES = new Set(["COMPLETED"]);
const FAILED_STATES = new Set(["FAILED", "DEAD_LETTER"]);

type RunLivePanelProps = {
  runId: string;
  initialRun: Run;
  initialEvents: RunEvent[];
};

export function RunLivePanel({ runId, initialRun, initialEvents }: RunLivePanelProps) {
  const [run, setRun] = useState<Run>(initialRun);
  const [events, setEvents] = useState<RunEvent[]>(initialEvents);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    const source = new EventSource(`/api/runs/${runId}/events/stream`);
    source.addEventListener("run-event", (message) => {
      try {
        const event = JSON.parse(message.data) as RunEvent;
        setEvents((prev) => (prev.some((item) => item.id === event.id) ? prev : [event, ...prev]));
      } catch {
        setError("Failed to parse run-event stream payload");
      }
    });
    source.addEventListener("run-state", (message) => {
      try {
        const nextRun = JSON.parse(message.data) as Run;
        setRun(nextRun);
      } catch {
        setError("Failed to parse run-state stream payload");
      }
    });
    source.addEventListener("error", () => {
      setError("SSE disconnected, retrying...");
    });
    source.addEventListener("done", () => {
      source.close();
    });

    // Warm-up fallback to avoid empty state before first stream tick.
    clientApi
      .listRunEvents(runId)
      .then((snapshot) => setEvents(snapshot))
      .catch(() => undefined);

    return () => {
      source.close();
    };
  }, [runId]);

  const activeStep = run.current_step ?? "PLANNER";
  const sortedEvents = useMemo(
    () =>
      [...events].sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      ),
    [events]
  );

  const terminal = useMemo(() => DONE_STATES.has(run.state) || FAILED_STATES.has(run.state), [run.state]);

  const onExecute = () => {
    startTransition(async () => {
      setError(null);
      try {
        await clientApi.executeRun(runId);
      } catch (e) {
        setError(mapApiErrorMessage(e, "Failed to start run"));
      }
    });
  };

  return (
    <div className="grid two">
      <section className="card stack">
        <h3>Run State</h3>
        <div className="step-row">
          <span className="pill">{run.state}</span>
          <span className="muted">attempt {run.attempt_count}</span>
          <span className="muted">retry {run.retry_count}</span>
        </div>
        <div className="stack">
          {STEPS.map((step) => {
            const stepState =
              step === activeStep ? "active" : STEPS.indexOf(step) < STEPS.indexOf(activeStep) ? "done" : "idle";
            return (
              <div key={step} className="step-row">
                <span className={`step-dot ${stepState === "active" ? "active" : stepState === "done" ? "done" : ""}`} />
                <strong>{step}</strong>
              </div>
            );
          })}
        </div>
        <div className="step-row">
          <button onClick={onExecute} disabled={pending || !terminal && run.state !== "QUEUED"}>
            {pending ? "Starting..." : "Start / Resume"}
          </button>
        </div>
        {error ? <p className="status-danger">{error}</p> : null}
      </section>

      <section className="card stack">
        <h3>Event Timeline</h3>
        <div className="timeline">
          {sortedEvents.map((event) => (
            <article className="timeline-item" key={event.id}>
              <div className="step-row">
                <strong>{event.event_type}</strong>
                {event.step ? <span className="pill">{event.step}</span> : null}
                <span className="muted">{new Date(event.created_at).toLocaleString()}</span>
              </div>
              {event.payload_json ? <pre>{JSON.stringify(event.payload_json, null, 2)}</pre> : null}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
