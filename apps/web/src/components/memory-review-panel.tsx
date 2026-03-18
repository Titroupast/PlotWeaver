"use client";

import { useMemo, useState, useTransition } from "react";

import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";
import type { MemoryDelta } from "@/lib/api/types";

type Props = {
  projectId: string;
  initialDeltas: MemoryDelta[];
};

export function MemoryReviewPanel({ projectId, initialDeltas }: Props) {
  const [deltas, setDeltas] = useState<MemoryDelta[]>(initialDeltas);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const pendingCount = useMemo(
    () => deltas.filter((item) => item.gate_status === "PENDING_REVIEW").length,
    [deltas]
  );

  const onDecision = (deltaId: string, decision: "MERGE" | "REJECT") => {
    startTransition(async () => {
      setError(null);
      try {
        const result = await clientApi.decideMemoryDelta(projectId, deltaId, { decision });
        setDeltas((prev) => prev.map((item) => (item.id === deltaId ? result.delta : item)));
      } catch (e) {
        setError(mapApiErrorMessage(e, "记忆决策提交失败"));
      }
    });
  };

  return (
    <section className="card stack">
      <div className="step-row">
        <h3>待人工确认 Delta</h3>
        <span className="pill">{pendingCount}</span>
      </div>

      {deltas.length === 0 ? <p className="muted">当前没有待确认记忆增量。</p> : null}

      <div className="timeline">
        {deltas.map((delta) => (
          <article className="timeline-item" key={delta.id}>
            <div className="step-row">
              <strong>{delta.delta_type}</strong>
              <span className="pill">{delta.gate_status}</span>
              <span className="muted">风险: {delta.risk_level}</span>
            </div>
            <p className="muted">来源 Run: {delta.run_id}</p>
            <pre>{JSON.stringify(delta.payload_json, null, 2)}</pre>
            {delta.gate_status === "PENDING_REVIEW" ? (
              <div className="step-row">
                <button disabled={pending} onClick={() => onDecision(delta.id, "MERGE")}>合并</button>
                <button className="secondary" disabled={pending} onClick={() => onDecision(delta.id, "REJECT")}>拒绝</button>
              </div>
            ) : null}
          </article>
        ))}
      </div>

      {error ? <p className="status-danger">{error}</p> : null}
    </section>
  );
}
