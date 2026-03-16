from __future__ import annotations

from pathlib import Path

from packages.contracts.constants import CONTRACT_VERSION
from packages.contracts.io import (
    chapter_meta_from_title_compat,
    load_characters_contract,
    normalize_memory_gate_from_review,
    normalize_outline_contract,
    normalize_review_contract,
    write_memory_gate_contract,
)


def test_outline_contract_roundtrip_from_legacy_payload() -> None:
    legacy_payload = {
        "chapter_goal": "Protect the capital city",
        "conflict": "A traitor inside the council leaks plans",
        "beats": ["Reveal betrayal", "Set trap", "Counterattack"],
        "foreshadowing": ["The seal ring appears twice"],
        "ending_hook": "A hidden letter points to the true mastermind",
    }

    normalized = normalize_outline_contract(legacy_payload, strict=True)
    assert normalized["contract_version"] == CONTRACT_VERSION
    assert normalized["chapter_goal"] == legacy_payload["chapter_goal"]


def test_review_contract_roundtrip_from_legacy_payload() -> None:
    legacy_payload = {
        "character_consistency_score": 88,
        "world_consistency_score": 86,
        "style_match_score": 84,
        "repetition_issues": [],
        "revision_suggestions": [
            "must_include check: all covered",
            "must_not_include check: no violations",
            "continuity_constraints check: pass",
        ],
    }

    normalized = normalize_review_contract(legacy_payload, strict=True)
    assert normalized["contract_version"] == CONTRACT_VERSION
    assert normalized["style_match_score"] == 84


def test_characters_legacy_name_is_mapped_and_id_is_generated(tmp_path: Path) -> None:
    payload_path = tmp_path / "characters.json"
    payload_path.write_text('{"characters":[{"name":"Luna","aliases":["Moonblade"]}]}', encoding="utf-8")

    normalized = load_characters_contract(payload_path)
    assert normalized["contract_version"] == CONTRACT_VERSION
    character = normalized["characters"][0]
    assert character["canonical_name"] == "Luna"
    assert character["display_name"] == "Luna"
    assert character["character_id"].startswith("char_legacy_")


def test_chapter_meta_can_be_built_from_title_compat(tmp_path: Path) -> None:
    output_path = tmp_path / "chapter_meta.json"
    payload = chapter_meta_from_title_compat(
        output_path,
        chapter_id="chapter_12",
        title="Storm Over South Gate",
        summary="Defenders prepare for the siege.",
    )
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["chapter_id"] == "chapter_12"
    assert payload["order_index"] == 12


def test_memory_gate_can_be_derived_and_written(tmp_path: Path) -> None:
    review_payload = {
        "character_consistency_score": 90,
        "world_consistency_score": 91,
        "style_match_score": 89,
        "repetition_issues": [],
    }
    gate_payload = normalize_memory_gate_from_review(
        review=review_payload,
        min_score=80,
        max_repetition=3,
    )
    assert gate_payload["contract_version"] == CONTRACT_VERSION
    assert gate_payload["pass"] is True
    assert gate_payload["recommended_action"] == "AUTO_MERGE"

    out_path = tmp_path / "memory_gate.json"
    written = write_memory_gate_contract(out_path, gate_payload)
    assert written["pass"] is True
