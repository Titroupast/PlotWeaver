from __future__ import annotations

import json
from pathlib import Path

from packages.contracts.constants import CONTRACT_VERSION
from packages.contracts.models import (
    ChapterMetaContract,
    CharactersContract,
    MemoryGateContract,
    OutlineContract,
    ReviewContract,
)


def test_contract_models_use_single_global_version() -> None:
    outline = OutlineContract(
        chapter_goal="x",
        conflict="y",
        beats=["a"],
        foreshadowing=["b"],
        ending_hook="z",
    )
    review = ReviewContract(
        character_consistency_score=90,
        world_consistency_score=90,
        style_match_score=90,
        repetition_issues=[],
        revision_suggestions=[
            "must_include check pass",
            "must_not_include check pass",
            "continuity_constraints check pass",
        ],
    )
    characters = CharactersContract(characters=[])
    chapter_meta = ChapterMetaContract(
        chapter_id="chapter_1",
        kind="NORMAL",
        title="t",
        order_index=1,
        status="GENERATED",
        summary="",
        created_at="2026-03-16T00:00:00Z",
        updated_at="2026-03-16T00:00:00Z",
    )
    memory_gate = MemoryGateContract(
        **{
            "pass": True,
            "issues": [],
            "recommended_action": "AUTO_MERGE",
        }
    )

    for model in (outline, review, characters, chapter_meta, memory_gate):
        assert model.contract_version == CONTRACT_VERSION


def test_schema_files_embed_same_contract_version() -> None:
    schema_root = Path(__file__).resolve().parents[1] / "schemas"
    schema_files = [
        schema_root / "outline.schema.json",
        schema_root / "review.schema.json",
        schema_root / "characters.schema.json",
        schema_root / "chapter_meta.schema.json",
        schema_root / "memory_gate.schema.json",
    ]
    for schema_file in schema_files:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        assert schema["properties"]["contract_version"]["default"] == CONTRACT_VERSION
