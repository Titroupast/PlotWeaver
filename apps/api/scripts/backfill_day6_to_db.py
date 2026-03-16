from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[3]
DAY6_INPUTS = ROOT / "novel-agent-day6" / "inputs" / "demo"
DAY6_OUTPUTS = ROOT / "novel-agent-day6" / "outputs" / "demo"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/plotweaver",
)


TENANT_NAME = "local-dev-tenant"
PROJECT_TITLE = "Demo Project"


def _sha256_json(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def main() -> None:
    engine = create_engine(DATABASE_URL, future=True)

    chapters_root = DAY6_INPUTS / "chapters"
    output_chapters_root = DAY6_OUTPUTS / "chapters"

    with engine.begin() as conn:
        tenant_id = conn.execute(
            text(
                """
                INSERT INTO tenants (name)
                VALUES (:name)
                ON CONFLICT DO NOTHING
                RETURNING id
                """
            ),
            {"name": TENANT_NAME},
        ).scalar()
        if tenant_id is None:
            tenant_id = conn.execute(text("SELECT id FROM tenants WHERE name=:name"), {"name": TENANT_NAME}).scalar_one()

        project_id = conn.execute(
            text(
                """
                INSERT INTO projects (tenant_id, title)
                VALUES (:tenant_id, :title)
                ON CONFLICT (tenant_id, title) WHERE deleted_at IS NULL DO NOTHING
                RETURNING id
                """
            ),
            {"tenant_id": tenant_id, "title": PROJECT_TITLE},
        ).scalar()
        if project_id is None:
            project_id = conn.execute(
                text("SELECT id FROM projects WHERE tenant_id=:tenant_id AND title=:title AND deleted_at IS NULL"),
                {"tenant_id": tenant_id, "title": PROJECT_TITLE},
            ).scalar_one()

        for chapter_dir in sorted(chapters_root.glob("chapter_*")):
            chapter_key = chapter_dir.name
            chapter_txt = (chapter_dir / "chapter.txt").read_text(encoding="utf-8") if (chapter_dir / "chapter.txt").exists() else ""
            title_txt = (chapter_dir / "title.txt").read_text(encoding="utf-8").replace("##", "").strip() if (chapter_dir / "title.txt").exists() else chapter_key
            chapter_meta_path = chapter_dir / "chapter_meta.json"
            if chapter_meta_path.exists():
                chapter_meta = json.loads(chapter_meta_path.read_text(encoding="utf-8"))
            else:
                order_index = int(chapter_key.replace("chapter_", ""))
                chapter_meta = {
                    "kind": "NORMAL",
                    "title": title_txt,
                    "subtitle": None,
                    "volume_id": None,
                    "arc_id": None,
                    "order_index": order_index,
                    "status": "GENERATED",
                    "summary": chapter_txt[:120],
                }

            chapter_id = conn.execute(
                text(
                    """
                    INSERT INTO chapters (
                        tenant_id, project_id, chapter_key, kind, title, subtitle, volume_id, arc_id,
                        order_index, status, summary
                    )
                    VALUES (
                        :tenant_id, :project_id, :chapter_key, :kind, :title, :subtitle, :volume_id, :arc_id,
                        :order_index, :status, :summary
                    )
                    ON CONFLICT (tenant_id, project_id, chapter_key)
                    DO UPDATE SET
                        kind=excluded.kind,
                        title=excluded.title,
                        subtitle=excluded.subtitle,
                        volume_id=excluded.volume_id,
                        arc_id=excluded.arc_id,
                        order_index=excluded.order_index,
                        status=excluded.status,
                        summary=excluded.summary,
                        updated_at=now()
                    RETURNING id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "chapter_key": chapter_key,
                    "kind": chapter_meta.get("kind", "NORMAL"),
                    "title": chapter_meta.get("title") or title_txt,
                    "subtitle": chapter_meta.get("subtitle"),
                    "volume_id": chapter_meta.get("volume_id"),
                    "arc_id": chapter_meta.get("arc_id"),
                    "order_index": chapter_meta.get("order_index") or int(chapter_key.replace("chapter_", "")),
                    "status": chapter_meta.get("status", "GENERATED"),
                    "summary": chapter_meta.get("summary", ""),
                },
            ).scalar_one()

            if chapter_txt:
                conn.execute(
                    text(
                        """
                        INSERT INTO chapter_versions (
                            tenant_id, chapter_id, version_no, source_type, storage_bucket, storage_key,
                            content_sha256, byte_size
                        ) VALUES (
                            :tenant_id, :chapter_id, 1, 'GENERATED', 'local-filesystem', :storage_key,
                            :content_sha256, :byte_size
                        )
                        ON CONFLICT (tenant_id, chapter_id, version_no) DO NOTHING
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "chapter_id": chapter_id,
                        "storage_key": str((chapter_dir / "chapter.txt").relative_to(ROOT)).replace("\\", "/"),
                        "content_sha256": hashlib.sha256(chapter_txt.encode("utf-8")).hexdigest(),
                        "byte_size": len(chapter_txt.encode("utf-8")),
                    },
                )

        out_dir = output_chapters_root / "chapter_005"
        outline = json.loads((out_dir / "outline.json").read_text(encoding="utf-8")) if (out_dir / "outline.json").exists() else None
        review = json.loads((out_dir / "review.json").read_text(encoding="utf-8")) if (out_dir / "review.json").exists() else None
        gate = json.loads((out_dir / "memory_gate.json").read_text(encoding="utf-8")) if (out_dir / "memory_gate.json").exists() else None

        if outline or review or gate:
            run_id = conn.execute(
                text(
                    """
                    INSERT INTO runs (tenant_id, project_id, state, idempotency_key)
                    VALUES (:tenant_id, :project_id, 'SUCCEEDED', :idempotency_key)
                    RETURNING id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "idempotency_key": "backfill-chapter-005",
                },
            ).scalar_one()

            for artifact_type, payload in (
                ("OUTLINE", outline),
                ("REVIEW", review),
                ("MEMORY_GATE", gate),
            ):
                if payload is None:
                    continue
                conn.execute(
                    text(
                        """
                        INSERT INTO run_artifacts (tenant_id, run_id, artifact_type, version_no, payload_json, payload_hash)
                        VALUES (:tenant_id, :run_id, :artifact_type, 1, CAST(:payload_json AS jsonb), :payload_hash)
                        ON CONFLICT (tenant_id, run_id, artifact_type, version_no) DO NOTHING
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "run_id": run_id,
                        "artifact_type": artifact_type,
                        "payload_json": json.dumps(payload, ensure_ascii=False),
                        "payload_hash": _sha256_json(payload),
                    },
                )

    print("Backfill completed.")


if __name__ == "__main__":
    main()
