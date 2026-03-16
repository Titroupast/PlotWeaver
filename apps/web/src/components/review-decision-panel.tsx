"use client";

import { useState, useTransition } from "react";

import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";
import type { Run } from "@/lib/api/types";

type ReviewDecisionPanelProps = {
  runId: string;
  runState: string;
};

export function ReviewDecisionPanel({ runId, runState }: ReviewDecisionPanelProps) {
  const [pending, startTransition] = useTransition();
  const [reason, setReason] = useState("");
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);

  const effectiveState = run?.state ?? runState;
  const visible = effectiveState === "WAITING_HUMAN_REVIEW";

  const submitDecision = (decision: "APPROVE" | "REQUEST_REWRITE" | "REJECT") => {
    startTransition(async () => {
      setError(null);
      try {
        const updated = await clientApi.humanReviewDecision(runId, decision, reason || undefined);
        setRun(updated);
      } catch (e) {
        setError(mapApiErrorMessage(e, "Failed to submit review decision"));
      }
    });
  };

  return (
    <section className="card stack">
      <h3>Human Review Decision</h3>
      <p className="muted">当前状态：{effectiveState}</p>
      {!visible ? (
        <p className="muted">当前 run 不需要人工复核。</p>
      ) : (
        <>
          <div>
            <label htmlFor="review-reason">Decision Reason (optional)</label>
            <textarea
              id="review-reason"
              value={reason}
              rows={3}
              onChange={(event) => setReason(event.target.value)}
              placeholder="记录审批/驳回理由，便于审计追踪"
            />
          </div>
          <div className="step-row">
            <button disabled={pending} onClick={() => submitDecision("APPROVE")}>
              Approve
            </button>
            <button className="secondary" disabled={pending} onClick={() => submitDecision("REQUEST_REWRITE")}>
              Request Rewrite
            </button>
            <button className="secondary" disabled={pending} onClick={() => submitDecision("REJECT")}>
              Reject
            </button>
          </div>
        </>
      )}
      {error ? <p className="status-danger">{error}</p> : null}
    </section>
  );
}
