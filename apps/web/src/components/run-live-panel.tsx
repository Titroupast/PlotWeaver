"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";

import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";
import type { Run, RunEvent } from "@/lib/api/types";

const STEPS = ["PLANNER", "WRITER", "REVIEWER", "MEMORY_CURATOR"];
const DONE_STATES = new Set(["SUCCEEDED"]);
const FAILED_STATES = new Set(["FAILED", "DEAD_LETTER", "CANCELLED"]);

type StreamStatus = "CONNECTING" | "STREAMING" | "STALE" | "POLLING" | "DONE";

type RunLivePanelProps = {
  runId: string;
  initialRun: Run;
  initialEvents: RunEvent[];
};

export function RunLivePanel({ runId, initialRun, initialEvents }: RunLivePanelProps) {
  const [run, setRun] = useState<Run>(initialRun);
  const [events, setEvents] = useState<RunEvent[]>(initialEvents);
  const [error, setError] = useState<string | null>(null);
  const [streamStatus, setStreamStatus] = useState<StreamStatus>("CONNECTING");
  const [pending, startTransition] = useTransition();
  const reconnectAttemptRef = useRef(0);
  const lastCursorRef = useRef<string | undefined>(findLatestCursor(initialEvents));

  useEffect(() => {
    let source: EventSource | null = null;
    let cancelled = false;
    let fallbackTimer: ReturnType<typeof setInterval> | null = null;

    const closeSource = () => {
      if (source) {
        source.close();
        source = null;
      }
    };

    const applyEvent = (event: RunEvent) => {
      setEvents((prev) => {
        if (prev.some((item) => item.id === event.id)) return prev;
        const next = [...prev, event];
        return next;
      });
      if (event.cursor) {
        lastCursorRef.current = event.cursor;
      }
    };

    const startPollingFallback = () => {
      if (fallbackTimer) return;
      setStreamStatus("POLLING");
      fallbackTimer = setInterval(async () => {
        if (cancelled) return;
        try {
          const [nextRun, deltaEvents] = await Promise.all([
            clientApi.getRun(runId),
            clientApi.listRunEvents(runId, lastCursorRef.current)
          ]);
          setRun(nextRun);
          deltaEvents.forEach(applyEvent);
          if (DONE_STATES.has(nextRun.state) || FAILED_STATES.has(nextRun.state)) {
            setStreamStatus("DONE");
            if (fallbackTimer) clearInterval(fallbackTimer);
          }
        } catch (e) {
          setError(mapApiErrorMessage(e, "Polling fallback failed"));
        }
      }, 3000);
    };

    const connectSse = () => {
      if (cancelled) return;
      setStreamStatus("CONNECTING");
      const query = lastCursorRef.current ? `?after_cursor=${encodeURIComponent(lastCursorRef.current)}` : "";
      source = new EventSource(`/api/runs/${runId}/events/stream${query}`);

      source.addEventListener("run-event", (message) => {
        try {
          const event = JSON.parse(message.data) as RunEvent;
          applyEvent(event);
          setStreamStatus("STREAMING");
          reconnectAttemptRef.current = 0;
        } catch {
          setError("Failed to parse run-event stream payload");
        }
      });

      source.addEventListener("run-state", (message) => {
        try {
          const nextRun = JSON.parse(message.data) as Run;
          setRun(nextRun);
          setStreamStatus("STREAMING");
        } catch {
          setError("Failed to parse run-state stream payload");
        }
      });

      source.addEventListener("done", () => {
        setStreamStatus("DONE");
        closeSource();
      });

      source.onerror = () => {
        closeSource();
        if (cancelled) return;
        reconnectAttemptRef.current += 1;
        setStreamStatus("STALE");

        if (reconnectAttemptRef.current >= 5) {
          setError("SSE unstable, switched to polling fallback");
          startPollingFallback();
          return;
        }

        const baseDelayMs = Math.min(15000, 1000 * 2 ** (reconnectAttemptRef.current - 1));
        const jitter = Math.round(baseDelayMs * (Math.random() * 0.4 - 0.2));
        setTimeout(connectSse, baseDelayMs + jitter);
      };
    };

    // Warm-up sync to avoid stale initial snapshot.
    clientApi
      .listRunEvents(runId)
      .then((snapshot) => {
        if (cancelled) return;
        setEvents(snapshot);
        lastCursorRef.current = findLatestCursor(snapshot);
      })
      .catch(() => undefined);

    connectSse();

    return () => {
      cancelled = true;
      closeSource();
      if (fallbackTimer) clearInterval(fallbackTimer);
    };
  }, [runId]);

  const activeStep = run.current_step ?? "PLANNER";
  const sortedEvents = useMemo(
    () => [...events].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()),
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
        <p className="muted">stream: {streamStatus}</p>
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
          <button onClick={onExecute} disabled={pending || (!terminal && run.state !== "QUEUED")}>
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

function findLatestCursor(events: RunEvent[]): string | undefined {
  const withCursor = events.filter((event) => event.cursor);
  if (withCursor.length === 0) return undefined;
  return withCursor[withCursor.length - 1].cursor ?? undefined;
}
