from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import CONTRACT_VERSION
from .models import ChapterKind, ChapterStatus, MergeStatus, MemoryGateAction


def _as_text_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _stable_character_id(entry: Dict[str, Any]) -> str:
    existing = str(entry.get("character_id") or "").strip()
    if existing:
        return existing
    canonical = (
        str(entry.get("canonical_name") or "").strip()
        or str(entry.get("display_name") or "").strip()
        or str(entry.get("name") or "").strip()
    )
    role = str(entry.get("role") or "").strip()
    age = entry.get("age")
    key = f"{canonical}|{role}|{age}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"char_legacy_{digest}"


def normalize_outline_payload(raw: Dict[str, Any], *, strict: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "chapter_goal": str(raw.get("chapter_goal", "")).strip(),
        "conflict": str(raw.get("conflict", "")).strip(),
        "beats": _as_text_list(raw.get("beats")),
        "foreshadowing": _as_text_list(raw.get("foreshadowing")),
        "ending_hook": str(raw.get("ending_hook", "")).strip(),
    }
    if strict:
        missing = [k for k in ("chapter_goal", "conflict", "ending_hook") if not payload[k]]
        if missing:
            raise ValueError(f"outline missing required non-empty fields: {', '.join(missing)}")
    return payload


def _ensure_review_requirement_checks(
    suggestions: List[str],
    *,
    strict: bool,
) -> List[str]:
    joined = "\n".join(suggestions).lower()
    required = [
        "must_include",
        "must_not_include",
        "continuity_constraints",
    ]
    missing = [item for item in required if item not in joined]
    if not missing:
        return suggestions

    if strict:
        raise ValueError(
            "review.revision_suggestions must explicitly include checks for: "
            + ", ".join(missing)
        )

    synthesized = list(suggestions)
    for token in missing:
        synthesized.append(
            f"硬约束检查（兼容补全）：{token} 检查结果缺失，请在后续 run 中显式给出结论。"
        )
    return synthesized


def normalize_review_payload(raw: Dict[str, Any], *, strict: bool) -> Dict[str, Any]:
    suggestions = _as_text_list(raw.get("revision_suggestions"))
    suggestions = _ensure_review_requirement_checks(suggestions, strict=strict)
    payload: Dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "character_consistency_score": int(raw.get("character_consistency_score", 0)),
        "world_consistency_score": int(raw.get("world_consistency_score", 0)),
        "style_match_score": int(raw.get("style_match_score", 0)),
        "repetition_issues": _as_text_list(raw.get("repetition_issues")),
        "revision_suggestions": suggestions,
    }
    return payload


def normalize_characters_payload(raw: Dict[str, Any], *, strict: bool) -> Dict[str, Any]:
    normalized_chars: List[Dict[str, Any]] = []
    for item in raw.get("characters", []) or []:
        if not isinstance(item, dict):
            if strict:
                raise ValueError("characters[] entries must be objects")
            continue

        canonical_name = (
            str(item.get("canonical_name") or "").strip()
            or str(item.get("display_name") or "").strip()
            or str(item.get("name") or "").strip()
        )
        if strict and not canonical_name:
            raise ValueError("character canonical_name/name is required")

        display_name = str(item.get("display_name") or canonical_name).strip()
        aliases = _as_text_list(item.get("aliases"))
        merge_status = str(item.get("merge_status") or MergeStatus.CONFIRMED.value).strip()
        if merge_status not in {v.value for v in MergeStatus}:
            merge_status = MergeStatus.PENDING_REVIEW.value

        normalized_chars.append(
            {
                "character_id": _stable_character_id(item),
                "canonical_name": canonical_name,
                "display_name": display_name,
                "aliases": aliases,
                "merge_status": merge_status,
                "role": str(item.get("role") or "").strip(),
                "age": int(item.get("age") or 0),
                "personality": _as_text_list(item.get("personality")),
                "background": _as_text_list(item.get("background")),
                "abilities": _as_text_list(item.get("abilities")),
                "limitations": _as_text_list(item.get("limitations")),
                "relationships": item.get("relationships")
                if isinstance(item.get("relationships"), dict)
                else {},
                "motivation": _as_text_list(item.get("motivation")),
                "key_memories": _as_text_list(item.get("key_memories")),
                "story_function": _as_text_list(item.get("story_function")),
                "beliefs": _as_text_list(item.get("beliefs")),
                "ambiguity": _as_text_list(item.get("ambiguity")),
                "identities": item.get("identities")
                if isinstance(item.get("identities"), list)
                else [],
            }
        )

    return {
        "contract_version": CONTRACT_VERSION,
        "characters": normalized_chars,
    }


def _parse_order_index(chapter_id: str) -> int:
    match = re.match(r"chapter_(\d+)$", chapter_id or "")
    if not match:
        return 0
    return int(match.group(1))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_min_chapter_meta(
    *,
    chapter_id: str,
    title: str,
    summary: str = "",
) -> Dict[str, Any]:
    now = _utc_now_iso()
    return {
        "contract_version": CONTRACT_VERSION,
        "chapter_id": chapter_id,
        "kind": ChapterKind.NORMAL.value,
        "title": title.strip(),
        "subtitle": None,
        "volume_id": None,
        "arc_id": None,
        "order_index": _parse_order_index(chapter_id),
        "status": ChapterStatus.GENERATED.value,
        "summary": summary.strip(),
        "created_at": now,
        "updated_at": now,
    }


def normalize_chapter_meta_payload(
    raw: Dict[str, Any],
    *,
    strict: bool,
    fallback_chapter_id: Optional[str] = None,
    fallback_title: Optional[str] = None,
) -> Dict[str, Any]:
    chapter_id = str(raw.get("chapter_id") or fallback_chapter_id or "").strip()
    title = str(raw.get("title") or fallback_title or "").strip()
    if strict and (not chapter_id or not title):
        raise ValueError("chapter_meta requires chapter_id and title")

    created_at = raw.get("created_at") or _utc_now_iso()
    updated_at = raw.get("updated_at") or created_at
    return {
        "contract_version": CONTRACT_VERSION,
        "chapter_id": chapter_id,
        "kind": str(raw.get("kind") or ChapterKind.NORMAL.value),
        "title": title,
        "subtitle": raw.get("subtitle"),
        "volume_id": raw.get("volume_id"),
        "arc_id": raw.get("arc_id"),
        "order_index": int(raw.get("order_index") or _parse_order_index(chapter_id)),
        "status": str(raw.get("status") or ChapterStatus.GENERATED.value),
        "summary": str(raw.get("summary") or "").strip(),
        "created_at": created_at,
        "updated_at": updated_at,
    }


def normalize_memory_gate_payload(raw: Dict[str, Any], *, strict: bool) -> Dict[str, Any]:
    if "pass" in raw:
        passed = bool(raw.get("pass"))
    else:
        passed = bool(raw.get("passed", False))
    recommended = str(raw.get("recommended_action") or "").strip()
    if not recommended:
        recommended = (
            MemoryGateAction.AUTO_MERGE.value
            if passed
            else MemoryGateAction.REVIEW_MANUALLY.value
        )
    if recommended not in {v.value for v in MemoryGateAction}:
        if strict:
            raise ValueError(f"invalid recommended_action: {recommended}")
        recommended = MemoryGateAction.REVIEW_MANUALLY.value
    return {
        "contract_version": CONTRACT_VERSION,
        "pass": passed,
        "issues": _as_text_list(raw.get("issues")),
        "recommended_action": recommended,
    }

