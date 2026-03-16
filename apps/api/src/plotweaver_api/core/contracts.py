from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from plotweaver_api.core.errors import ValidationError

# Monorepo path for shared contracts package
_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from packages.contracts.adapters import (  # type: ignore  # noqa: E402
    normalize_chapter_meta_payload,
    normalize_memory_gate_payload,
)
from packages.contracts.io import normalize_outline_contract, normalize_review_contract  # type: ignore  # noqa: E402


REQUIREMENT_REQUIRED_KEYS = {
    "chapter_goal",
    "must_include",
    "must_not_include",
    "tone",
    "continuity_constraints",
    "target_length",
    "optional_notes",
}


def build_payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def validate_requirement_payload(payload: dict[str, Any]) -> dict[str, Any]:
    missing = [k for k in sorted(REQUIREMENT_REQUIRED_KEYS) if k not in payload]
    if missing:
        raise ValidationError(
            "Requirement payload missing required keys",
            details={"missing_keys": missing},
        )
    return payload


def validate_artifact_payload(artifact_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        if artifact_type == "OUTLINE":
            return normalize_outline_contract(payload, strict=True)
        if artifact_type == "REVIEW":
            return normalize_review_contract(payload, strict=True)
        if artifact_type == "MEMORY_GATE":
            return normalize_memory_gate_payload(payload, strict=True)
        if artifact_type == "CHAPTER_META":
            return normalize_chapter_meta_payload(payload, strict=True)
    except Exception as exc:
        raise ValidationError(
            "Artifact payload failed contract validation",
            details={"artifact_type": artifact_type, "error": str(exc)},
        ) from exc

    raise ValidationError(
        "Unsupported artifact_type for contract validation",
        details={"artifact_type": artifact_type},
    )
