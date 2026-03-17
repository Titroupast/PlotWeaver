import { NextRequest, NextResponse } from "next/server";

type JsonRecord = Record<string, unknown>;

type MockProject = {
  id: string;
  tenant_id: string;
  title: string;
  description: string;
  language: string;
  status: string;
  created_at: string;
  updated_at: string;
};

type MockChapter = {
  id: string;
  project_id: string;
  chapter_key: string;
  kind: string;
  title: string;
  order_index: number;
  status: string;
  summary: string;
  created_at: string;
  updated_at: string;
};

export const dynamic = "force-dynamic";

const nowIso = "2026-03-16T00:00:00Z";
const STEP_ORDER = ["PLANNER", "WRITER", "REVIEWER", "MEMORY_CURATOR"] as const;
let projectCounter = 2;
let runState = "QUEUED";
let runStepIndex = 0;
let eventCounter = 1;
const producedArtifacts: JsonRecord[] = [];
const events: JsonRecord[] = [];

const projects = new Map<string, MockProject>([
  [
    "proj-1",
    {
      id: "proj-1",
      tenant_id: "00000000-0000-0000-0000-000000000001",
      title: "Demo Project",
      description: "Mock data for e2e key path",
      language: "zh-CN",
      status: "ACTIVE",
      created_at: nowIso,
      updated_at: nowIso
    }
  ]
]);

const chapters = new Map<string, MockChapter[]>([
  [
    "proj-1",
    [
      {
        id: "chap-1",
        project_id: "proj-1",
        chapter_key: "chapter_1",
        kind: "NORMAL",
        title: "Chapter One",
        order_index: 1,
        status: "GENERATED",
        summary: "A generated opening chapter.",
        created_at: nowIso,
        updated_at: nowIso
      }
    ]
  ]
]);

function json(data: JsonRecord | JsonRecord[], status = 200): NextResponse {
  return NextResponse.json(data, { status });
}

function routeOf(parts: string[]): string {
  return `/${parts.join("/")}`;
}

function nextStepName(): string | null {
  if (runStepIndex >= STEP_ORDER.length) return null;
  return STEP_ORDER[runStepIndex];
}

function makeRun() {
  return {
    id: "run-1",
    project_id: "proj-1",
    state: runState,
    idempotency_key: "idem-1",
    attempt_count: 1,
    retry_count: 0,
    current_step: nextStepName(),
    checkpoint_json: {
      completed_steps: STEP_ORDER.slice(0, runStepIndex),
      artifact_ids: {}
    },
    created_at: nowIso,
    updated_at: nowIso
  };
}

function pushEvent(event_type: string, step: string | null, payload_json: JsonRecord) {
  events.push({
    id: `evt-${eventCounter}`,
    run_id: "run-1",
    event_type,
    step,
    payload_json,
    created_at: nowIso,
    cursor: `${nowIso}|evt-${eventCounter}`
  });
  eventCounter += 1;
}

function artifactForStep(step: string): JsonRecord {
  if (step === "PLANNER") {
    return {
      id: "art-outline",
      run_id: "run-1",
      artifact_type: "OUTLINE",
      version_no: 1,
      payload_json: {
        contract_version: "1.0.0",
        chapter_goal: "推进主要冲突",
        conflict: "主角面临外部阻力",
        beats: ["开场冲突", "策略转折", "留下钩子"],
        foreshadowing: ["神秘线索"],
        ending_hook: "新变量出现"
      },
      payload_hash: "x",
      created_at: nowIso
    };
  }
  if (step === "WRITER") {
    return {
      id: "art-meta",
      run_id: "run-1",
      artifact_type: "CHAPTER_META",
      version_no: 1,
      payload_json: {
        contract_version: "1.0.0",
        chapter_id: "chapter_1",
        kind: "NORMAL",
        title: "风暴前夜",
        subtitle: null,
        volume_id: null,
        arc_id: null,
        order_index: 1,
        status: "GENERATED",
        summary: "主角在危机前夜做出关键决策",
        created_at: nowIso,
        updated_at: nowIso
      },
      payload_hash: "x",
      created_at: nowIso
    };
  }
  if (step === "REVIEWER") {
    return {
      id: "art-review",
      run_id: "run-1",
      artifact_type: "REVIEW",
      version_no: 1,
      payload_json: {
        contract_version: "1.0.0",
        character_consistency_score: 90,
        world_consistency_score: 90,
        style_match_score: 88,
        repetition_issues: [],
        revision_suggestions: [
          "must_include 检查通过",
          "must_not_include 检查通过",
          "continuity_constraints 检查通过"
        ]
      },
      payload_hash: "x",
      created_at: nowIso
    };
  }
  return {
    id: "art-gate",
    run_id: "run-1",
    artifact_type: "MEMORY_GATE",
    version_no: 1,
    payload_json: { contract_version: "1.0.0", pass: true, issues: [], recommended_action: "AUTO_MERGE" },
    payload_hash: "x",
    created_at: nowIso
  };
}

function sseLine(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ segments: string[] }> }) {
  const segments = (await params).segments;
  const route = routeOf(segments);

  if (route === "/projects") {
    return json(Array.from(projects.values()));
  }

  if (segments.length === 2 && segments[0] === "projects") {
    const project = projects.get(segments[1]);
    if (!project) return json({ code: "NOT_FOUND", message: `Unknown project ${segments[1]}` }, 404);
    return json(project);
  }

  if (segments.length === 3 && segments[0] === "projects" && segments[2] === "chapters") {
    return json(chapters.get(segments[1]) ?? []);
  }

  if (
    segments.length === 5 &&
    segments[0] === "projects" &&
    segments[2] === "chapters" &&
    segments[4] === "latest-content"
  ) {
    const chapterId = segments[3];
    return json({
      chapter_id: chapterId,
      version_no: 1,
      storage_bucket: "mock-local",
      storage_key: `projects/${segments[1]}/chapters/${chapterId}/v1.txt`,
      content_sha256: "mock-sha256",
      byte_size: 58,
      content: "这是 mock 正文输出。主角在压力中做出关键抉择，故事继续推进。",
      created_at: nowIso
    });
  }

  if (route === "/runs/run-1") {
    return json(makeRun());
  }

  if (route === "/runs/run-1/events") {
    const afterCursor = request.nextUrl.searchParams.get("after_cursor");
    if (!afterCursor) return json(events);
    return json([]);
  }

  if (route === "/runs/run-1/artifacts") {
    return json(producedArtifacts);
  }

  if (route === "/runs/run-1/stream") {
    const encoder = new TextEncoder();
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        const latestEvent = events[events.length - 1];
        if (latestEvent) {
          controller.enqueue(encoder.encode(sseLine("run-event", latestEvent)));
        }
        controller.enqueue(encoder.encode(sseLine("run-state", makeRun())));
        if (runState === "SUCCEEDED" || runState === "FAILED") {
          controller.enqueue(encoder.encode(sseLine("done", { run_id: "run-1", state: runState })));
        }
        controller.close();
      }
    });
    return new Response(body, {
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive"
      }
    });
  }

  return json({ code: "NOT_FOUND", message: `Unhandled mock route ${route}` }, 404);
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ segments: string[] }> }) {
  const segments = (await params).segments;
  const route = routeOf(segments);
  const body = (await request.json().catch(() => ({}))) as JsonRecord;

  if (route === "/projects") {
    const id = `proj-${projectCounter++}`;
    const created: MockProject = {
      id,
      tenant_id: "00000000-0000-0000-0000-000000000001",
      title: String(body.title ?? "Untitled Project"),
      description: String(body.description ?? ""),
      language: "zh-CN",
      status: "ACTIVE",
      created_at: nowIso,
      updated_at: nowIso
    };
    projects.set(id, created);
    chapters.set(id, [
      {
        id: `${id}-chap-1`,
        project_id: id,
        chapter_key: "chapter_1",
        kind: "NORMAL",
        title: "Chapter One",
        order_index: 1,
        status: "GENERATED",
        summary: "Auto-created first chapter",
        created_at: nowIso,
        updated_at: nowIso
      }
    ]);
    return json(created, 201);
  }

  if (segments.length === 3 && segments[0] === "projects" && segments[2] === "requirements") {
    return json(
      {
        id: "req-1",
        project_id: segments[1],
        chapter_goal: String(body.chapter_goal ?? ""),
        payload_json: body.payload_json ?? {},
        payload_hash: "req-hash",
        source: "WEB",
        created_at: nowIso
      },
      201
    );
  }

  if (route === "/runs") {
    runState = "QUEUED";
    runStepIndex = 0;
    producedArtifacts.length = 0;
    events.length = 0;
    eventCounter = 1;
    return json(makeRun(), 201);
  }

  if (route === "/runs/run-1/execute") {
    if (runStepIndex < STEP_ORDER.length) {
      const step = STEP_ORDER[runStepIndex];
      pushEvent("STEP_STARTED", step, { step });
      producedArtifacts.push(artifactForStep(step));
      pushEvent("STEP_COMPLETED", step, { step, artifact_type: producedArtifacts[producedArtifacts.length - 1].artifact_type as string });
      runStepIndex += 1;
      if (runStepIndex < STEP_ORDER.length) {
        runState = "WAITING_USER_APPROVAL";
        pushEvent("STEP_AWAITING_APPROVAL", STEP_ORDER[runStepIndex], { next_step: STEP_ORDER[runStepIndex] });
      } else {
        runState = "SUCCEEDED";
        pushEvent("RUN_SUCCEEDED", "MEMORY_CURATOR", { completed_steps: STEP_ORDER });
      }
    }
    return json(makeRun(), 200);
  }

  if (route === "/runs/run-1/review-decision") {
    const decision = String(body.decision ?? "");
    if (decision === "REJECT") {
      runState = "FAILED";
    } else if (decision === "REQUEST_REWRITE") {
      runState = "WAITING_USER_APPROVAL";
      runStepIndex = 1;
    } else {
      runState = "SUCCEEDED";
    }
    return json(makeRun(), 200);
  }

  return json({ code: "NOT_FOUND", message: `Unhandled mock route ${route}` }, 404);
}