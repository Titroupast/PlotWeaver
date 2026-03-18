"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";

import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";
import type { Artifact, Run, RunEvent } from "@/lib/api/types";

const STEPS = ["PLANNER", "WRITER", "REVIEWER", "MEMORY_CURATOR"];
const STEP_BY_ARTIFACT_TYPE: Record<string, string> = {
  OUTLINE: "PLANNER",
  CHAPTER_META: "WRITER",
  REVIEW: "REVIEWER",
  MEMORY_GATE: "MEMORY_CURATOR"
};
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
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [streamStatus, setStreamStatus] = useState<StreamStatus>("CONNECTING");
  const [pending, startTransition] = useTransition();
  const reconnectAttemptRef = useRef(0);
  const lastCursorRef = useRef<string | undefined>(findLatestCursor(initialEvents));

  useEffect(() => {
    clientApi
      .listArtifacts(runId)
      .then((items) => setArtifacts(items))
      .catch(() => undefined);
  }, [runId]);

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
        return [...prev, event];
      });
      if (event.cursor) {
        lastCursorRef.current = event.cursor;
      }
      if (event.event_type === "STEP_COMPLETED") {
        clientApi
          .listArtifacts(runId)
          .then((items) => setArtifacts(items))
          .catch(() => undefined);
      }
    };

    const startPollingFallback = () => {
      if (fallbackTimer) return;
      setStreamStatus("POLLING");
      fallbackTimer = setInterval(async () => {
        if (cancelled) return;
        try {
          const [nextRun, deltaEvents, nextArtifacts] = await Promise.all([
            clientApi.getRun(runId),
            clientApi.listRunEvents(runId, lastCursorRef.current),
            clientApi.listArtifacts(runId)
          ]);
          setRun(nextRun);
          setArtifacts(nextArtifacts);
          deltaEvents.forEach(applyEvent);
          if (DONE_STATES.has(nextRun.state) || FAILED_STATES.has(nextRun.state)) {
            setStreamStatus("DONE");
            if (fallbackTimer) clearInterval(fallbackTimer);
          }
        } catch (e) {
          setError(mapApiErrorMessage(e, "轮询失败"));
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
          setError("解析事件流失败");
        }
      });

      source.addEventListener("run-state", (message) => {
        try {
          const nextRun = JSON.parse(message.data) as Run;
          setRun(nextRun);
          setStreamStatus("STREAMING");
        } catch {
          setError("解析状态流失败");
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
          setError("SSE 不稳定，已切换到轮询");
          startPollingFallback();
          return;
        }

        const baseDelayMs = Math.min(15000, 1000 * 2 ** (reconnectAttemptRef.current - 1));
        const jitter = Math.round(baseDelayMs * (Math.random() * 0.4 - 0.2));
        setTimeout(connectSse, baseDelayMs + jitter);
      };
    };

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
  const sortedArtifacts = useMemo(
    () => [...artifacts].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()),
    [artifacts]
  );
  const terminal = useMemo(() => DONE_STATES.has(run.state) || FAILED_STATES.has(run.state), [run.state]);
  const runUiStatus = useMemo(() => {
    if (run.state === "WAITING_HUMAN_REVIEW") return "需人工复核";
    if (run.state === "WAITING_USER_APPROVAL") return "等待继续";
    if (DONE_STATES.has(run.state)) return "已完成";
    return "执行中";
  }, [run.state]);

  const canRunNext = run.state === "QUEUED" || run.state === "WAITING_USER_APPROVAL" || run.state === "RETRYING";

  const onExecute = () => {
    startTransition(async () => {
      setError(null);
      try {
        await clientApi.executeRun(runId, { auto_continue: false });
      } catch (e) {
        setError(mapApiErrorMessage(e, "启动下一步失败"));
      }
    });
  };

  return (
    <div className="stack">
      <div className="grid two">
        <section className="card stack">
          <h3>运行状态</h3>
          <div className="step-row">
            <span className="pill">{run.state}</span>
            <span className="muted">{runUiStatus}</span>
            <span className="muted">尝试 {run.attempt_count}</span>
            <span className="muted">重试 {run.retry_count}</span>
          </div>
          <p className="muted">流状态: {streamStatus}</p>
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
            <button onClick={onExecute} disabled={pending || terminal || !canRunNext}>
              {pending ? "执行中..." : run.state === "QUEUED" ? "开始第一步" : "继续下一步"}
            </button>
          </div>
          {error ? <p className="status-danger">{error}</p> : null}
        </section>

        <section className="card stack">
          <h3>阶段输出（模型结果）</h3>
          <div className="timeline">
            {sortedArtifacts.length === 0 ? (
              <p className="muted">暂无产物，先执行第一步。</p>
            ) : (
              sortedArtifacts.map((artifact) => (
                <article className="timeline-item" key={artifact.id}>
                  <div className="step-row">
                    <strong>{artifact.artifact_type}</strong>
                    <span className="muted">v{artifact.version_no}</span>
                    {(() => {
                      const meta = findStepMetaFromEvents(sortedEvents, STEP_BY_ARTIFACT_TYPE[artifact.artifact_type]);
                      if (!meta) return null;
                      return (
                        <>
                          <span className="pill">{meta.llm_used ? "已调用模型" : "回退默认"}</span>
                          {meta.llm_error ? <span className="status-danger">错误: {meta.llm_error}</span> : null}
                        </>
                      );
                    })()}
                  </div>
                  <pre>{JSON.stringify(artifact.payload_json, null, 2)}</pre>
                </article>
              ))
            )}
          </div>
        </section>
      </div>

      <section className="card stack">
        <h3>事件时间线</h3>
        <div className="timeline">
          {sortedEvents.map((event) => (
            <article className="timeline-item" key={event.id}>
              <div className="step-row">
                <strong>{event.event_type}</strong>
                {event.step ? <span className="pill">{event.step}</span> : null}
                <span className="muted">{formatTimestamp(event.created_at)}</span>
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

function findStepMetaFromEvents(
  events: RunEvent[],
  step: string | undefined
): { llm_used: boolean; llm_error: string | null } | null {
  if (!step) return null;
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const evt = events[i];
    if (evt.event_type !== "STEP_COMPLETED" || evt.step !== step) continue;
    const payload = evt.payload_json ?? {};
    const llmUsed = Boolean(payload.llm_used);
    const llmError = typeof payload.llm_error === "string" ? payload.llm_error : null;
    return { llm_used: llmUsed, llm_error: llmError };
  }
  return null;
}


function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toISOString().replace('T', ' ').replace('Z', ' UTC');
}

