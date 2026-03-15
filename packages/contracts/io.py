from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .adapters import (
    build_min_chapter_meta,
    normalize_chapter_meta_payload,
    normalize_characters_payload,
    normalize_memory_gate_payload,
    normalize_outline_payload,
    normalize_review_payload,
)
from .models import (
    ChapterMetaContract,
    CharactersContract,
    MemoryGateContract,
    OutlineContract,
    ReviewContract,
)


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_outline_contract(raw: Dict[str, Any], *, strict: bool) -> Dict[str, Any]:
    payload = normalize_outline_payload(raw, strict=strict)
    validated = OutlineContract.model_validate(payload)
    return validated.model_dump()


def normalize_review_contract(raw: Dict[str, Any], *, strict: bool) -> Dict[str, Any]:
    payload = normalize_review_payload(raw, strict=strict)
    validated = ReviewContract.model_validate(payload)
    return validated.model_dump()


def load_characters_contract(path: Path) -> Dict[str, Any]:
    if not path.exists():
        payload = normalize_characters_payload({"characters": []}, strict=False)
        validated = CharactersContract.model_validate(payload)
        return validated.model_dump()

    raw = _read_json(path)
    payload = normalize_characters_payload(raw, strict=False)
    validated = CharactersContract.model_validate(payload)
    return validated.model_dump()


def write_characters_contract(path: Path, raw: Dict[str, Any], *, strict: bool) -> Dict[str, Any]:
    payload = normalize_characters_payload(raw, strict=strict)
    validated = CharactersContract.model_validate(payload)
    data = validated.model_dump()
    _write_json(path, data)
    return data


def write_outline_contract(path: Path, raw: Dict[str, Any]) -> Dict[str, Any]:
    data = normalize_outline_contract(raw, strict=True)
    _write_json(path, data)
    return data


def write_review_contract(path: Path, raw: Dict[str, Any]) -> Dict[str, Any]:
    data = normalize_review_contract(raw, strict=True)
    _write_json(path, data)
    return data


def write_chapter_meta_contract(
    path: Path,
    raw: Dict[str, Any],
    *,
    fallback_chapter_id: Optional[str] = None,
    fallback_title: Optional[str] = None,
) -> Dict[str, Any]:
    payload = normalize_chapter_meta_payload(
        raw,
        strict=True,
        fallback_chapter_id=fallback_chapter_id,
        fallback_title=fallback_title,
    )
    validated = ChapterMetaContract.model_validate(payload)
    data = validated.model_dump(mode="json")
    _write_json(path, data)
    return data


def chapter_meta_from_title_compat(path: Path, *, chapter_id: str, title: str, summary: str = "") -> Dict[str, Any]:
    payload = build_min_chapter_meta(chapter_id=chapter_id, title=title, summary=summary)
    validated = ChapterMetaContract.model_validate(payload)
    data = validated.model_dump(mode="json")
    _write_json(path, data)
    return data


def write_memory_gate_contract(path: Path, raw: Dict[str, Any]) -> Dict[str, Any]:
    payload = normalize_memory_gate_payload(raw, strict=True)
    validated = MemoryGateContract.model_validate(payload)
    data = validated.model_dump(mode="json", by_alias=True)
    _write_json(path, data)
    return data


def normalize_memory_gate_from_review(
    *,
    review: Dict[str, Any],
    min_score: int,
    max_repetition: int,
) -> Dict[str, Any]:
    issues = []
    for key in ("character_consistency_score", "world_consistency_score", "style_match_score"):
        if int(review.get(key, 0)) < min_score:
            issues.append(f"{key}<{min_score}")
    repetition_count = len(review.get("repetition_issues", []) or [])
    if repetition_count > max_repetition:
        issues.append(f"repetition_issues>{max_repetition}")
    raw = {
        "pass": len(issues) == 0,
        "issues": issues,
        "recommended_action": "AUTO_MERGE" if not issues else "REVIEW_MANUALLY",
    }
    payload = normalize_memory_gate_payload(raw, strict=True)
    validated = MemoryGateContract.model_validate(payload)
    return validated.model_dump(mode="json", by_alias=True)

