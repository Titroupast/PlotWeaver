"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";

import { ArtifactReview } from "@/components/artifact-review";
import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";
import type { Artifact, Run, RunEvent } from "@/lib/api/types";

const STEPS = ["PLANNER", "WRITER", "REVIEWER", "MEMORY_CURATOR"];
type AgentStep = (typeof STEPS)[number];
export type { AgentStep };

const STEP_BY_ARTIFACT_TYPE: Record<string, AgentStep> = {
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
  fixedStep?: AgentStep;
};

export function RunLivePanel({ runId, initialRun, initialEvents, fixedStep }: RunLivePanelProps) {
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
  const canRunFixedStep = !terminal && canRunNext;

  const onExecute = () => {
    startTransition(async () => {
      setError(null);
      try {
        if (fixedStep) {
          await clientApi.executeRun(runId, { auto_continue: false, resume_from_step: fixedStep });
          return;
        }
        await clientApi.executeRun(runId, { auto_continue: false });
      } catch (e) {
        setError(mapApiErrorMessage(e, fixedStep ? `从 ${fixedStep} 重生成失败` : "启动下一步失败"));
      }
    });
  };

  const displayArtifacts = useMemo(() => {
    if (!fixedStep) return sortedArtifacts;
    return sortedArtifacts.filter((artifact) => STEP_BY_ARTIFACT_TYPE[artifact.artifact_type] === fixedStep);
  }, [sortedArtifacts, fixedStep]);

  const displayEvents = useMemo(() => {
    if (!fixedStep) return sortedEvents;
    return sortedEvents.filter((event) => {
      if (event.step === fixedStep) return true;
      return event.event_type.startsWith("RUN_");
    });
  }, [sortedEvents, fixedStep]);

  const businessEvents = useMemo(
    () => displayEvents.filter((event) => ["RUN_EXECUTION_STARTED", "STEP_STARTED", "STEP_COMPLETED", "STEP_AWAITING_APPROVAL", "HUMAN_REVIEW_REQUIRED", "RUN_SUCCEEDED", "RUN_FAILED"].includes(event.event_type)),
    [displayEvents]
  );

  const riskSummary = useMemo(() => {
    const latestReview = [...sortedArtifacts].reverse().find((item) => item.artifact_type === "REVIEW");
    if (!latestReview) return null;
    const payload = latestReview.payload_json as Record<string, unknown>;
    const issues = Array.isArray(payload.repetition_issues)
      ? payload.repetition_issues.filter((x): x is string => typeof x === "string")
      : [];
    const suggestions = Array.isArray(payload.revision_suggestions)
      ? payload.revision_suggestions.filter((x): x is string => typeof x === "string")
      : [];
    const score = typeof payload.style_match_score === "number" ? payload.style_match_score : null;
    if (issues.length === 0 && suggestions.length === 0 && score !== null && score >= 85) return null;
    return {
      score,
      issues: issues.slice(0, 3),
      suggestions: suggestions.slice(0, 2)
    };
  }, [sortedArtifacts]);

  const panelTitle = fixedStep ? `${fixedStep} 智能体` : "运行状态";

  return (
    <div className="stack" id="run-live-panel">
      <section className="card stack" aria-live="polite">
        <h3>执行摘要</h3>
        <div className="step-row">
          <span className="pill">{run.state}</span>
          <span className="muted">{runUiStatus}</span>
          <span className="muted">尝试 {run.attempt_count}</span>
          <span className="muted">重试 {run.retry_count}</span>
          <span className="muted">流状态: {streamStatus}</span>
        </div>
        {riskSummary ? (
          <div className="risk-banner">
            <strong>风险提醒</strong>
            {riskSummary.score !== null ? <span className="pill">风格分 {riskSummary.score}</span> : null}
            {riskSummary.issues.map((issue) => (
              <p key={issue}>{issue}</p>
            ))}
            {riskSummary.suggestions.map((sug) => (
              <p className="muted" key={sug}>
                建议：{sug}
              </p>
            ))}
          </div>
        ) : (
          <p className="status-ok">当前未检测到明显高风险冲突。</p>
        )}
      </section>

      <div className="grid two">
        <section className="card stack">
          <h3>{panelTitle}</h3>
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
            <button
              type="button"
              className="action-merge"
              onClick={onExecute}
              disabled={pending || (fixedStep ? !canRunFixedStep : !canRunNext)}
            >
              <span className="btn-text">
                {pending ? "执行中..." : fixedStep ? `从 ${fixedStep} 重生成` : run.state === "QUEUED" ? "开始第一步" : "继续下一步"}
              </span>
            </button>
          </div>
          {error ? <p className="status-danger" role="status">{error}</p> : null}
        </section>

        <section className="card stack">
          <h3>{fixedStep ? `${fixedStep} 阶段输出` : "阶段输出（可编辑）"}</h3>
          {displayArtifacts.length === 0 ? (
            <p className="muted">暂无产物，先执行第一步。</p>
          ) : (
            <ArtifactReview runId={runId} artifacts={displayArtifacts} />
          )}
        </section>
      </div>

      <section className="card stack">
        <h3>{fixedStep ? `${fixedStep} 事件流` : "事件流"}</h3>
        <div className="timeline">
          {businessEvents.map((event) => (
            <article className="timeline-item" key={event.id}>
              <div className="step-row">
                <strong>{EVENT_LABELS[event.event_type] ?? event.event_type}</strong>
                {event.step ? <span className="pill">{event.step}</span> : null}
                <span className="muted">{formatTimestamp(event.created_at)}</span>
              </div>
            </article>
          ))}
        </div>
        <details>
          <summary>展开技术详情（调试）</summary>
          <div className="timeline">
            {displayEvents.map((event) => (
              <article className="timeline-item" key={`${event.id}-raw`}>
                <div className="step-row">
                  <strong>{event.event_type}</strong>
                  {event.step ? <span className="pill">{event.step}</span> : null}
                  <span className="muted">{formatTimestamp(event.created_at)}</span>
                </div>
                {event.payload_json ? <pre>{JSON.stringify(event.payload_json, null, 2)}</pre> : null}
              </article>
            ))}
          </div>
        </details>
      </section>
    </div>
  );
}

const EVENT_LABELS: Record<string, string> = {
  RUN_EXECUTION_STARTED: "运行开始",
  STEP_STARTED: "步骤开始",
  STEP_COMPLETED: "步骤完成",
  STEP_AWAITING_APPROVAL: "等待人工确认",
  HUMAN_REVIEW_REQUIRED: "需要人工复核",
  RUN_SUCCEEDED: "运行成功",
  RUN_FAILED: "运行失败"
};

function findLatestCursor(events: RunEvent[]): string | undefined {
  const withCursor = events.filter((event) => event.cursor);
  if (withCursor.length === 0) return undefined;
  return withCursor[withCursor.length - 1].cursor ?? undefined;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toISOString().replace("T", " ").replace("Z", " UTC");
}
