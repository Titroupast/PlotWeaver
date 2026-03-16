from __future__ import annotations

from pathlib import Path

import pytest

from packages.contracts.adapters import (
    normalize_chapter_meta_payload,
    normalize_characters_payload,
    normalize_memory_gate_payload,
    normalize_review_payload,
)
from packages.contracts.generate_schemas import main as generate_all_schemas
from packages.contracts.io import (
    load_characters_contract,
    write_chapter_meta_contract,
    write_outline_contract,
    write_review_contract,
)


def test_non_strict_review_auto_fills_required_check_tokens() -> None:
    payload = normalize_review_payload(
        {
            "character_consistency_score": 70,
            "world_consistency_score": 70,
            "style_match_score": 70,
            "repetition_issues": [],
            "revision_suggestions": ["generic advice"],
        },
        strict=False,
    )
    text = "\n".join(payload["revision_suggestions"]).lower()
    assert "must_include" in text
    assert "must_not_include" in text
    assert "continuity_constraints" in text


def test_normalize_characters_strict_rejects_non_object_items() -> None:
    with pytest.raises(ValueError):
        normalize_characters_payload({"characters": ["bad"]}, strict=True)


def test_normalize_memory_gate_non_strict_recovers_invalid_action() -> None:
    payload = normalize_memory_gate_payload(
        {"pass": False, "issues": ["x"], "recommended_action": "BAD_ACTION"},
        strict=False,
    )
    assert payload["recommended_action"] == "REVIEW_MANUALLY"


def test_normalize_chapter_meta_strict_requires_required_fields() -> None:
    with pytest.raises(ValueError):
        normalize_chapter_meta_payload({}, strict=True)


def test_write_outline_and_review_contract_files(tmp_path: Path) -> None:
    outline_path = tmp_path / "outline.json"
    review_path = tmp_path / "review.json"

    write_outline_contract(
        outline_path,
        {
            "chapter_goal": "goal",
            "conflict": "conflict",
            "beats": ["b1"],
            "foreshadowing": [],
            "ending_hook": "hook",
        },
    )
    write_review_contract(
        review_path,
        {
            "character_consistency_score": 90,
            "world_consistency_score": 90,
            "style_match_score": 90,
            "repetition_issues": [],
            "revision_suggestions": [
                "must_include checked",
                "must_not_include checked",
                "continuity_constraints checked",
            ],
        },
    )
    assert outline_path.exists()
    assert review_path.exists()


def test_write_chapter_meta_uses_fallback_values(tmp_path: Path) -> None:
    output_path = tmp_path / "chapter_meta.json"
    payload = write_chapter_meta_contract(
        output_path,
        {"summary": "fallback test"},
        fallback_chapter_id="chapter_2",
        fallback_title="Fallback title",
    )
    assert payload["chapter_id"] == "chapter_2"
    assert payload["title"] == "Fallback title"


def test_load_characters_contract_missing_file_returns_empty_contract(tmp_path: Path) -> None:
    payload = load_characters_contract(tmp_path / "missing_characters.json")
    assert payload["characters"] == []


def test_generate_all_schemas_main_runs() -> None:
    generate_all_schemas()
