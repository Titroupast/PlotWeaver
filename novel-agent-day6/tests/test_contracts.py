from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import validate

from packages.contracts.adapters import (
    build_min_chapter_meta,
    normalize_characters_payload,
    normalize_review_payload,
)
from packages.contracts.io import normalize_memory_gate_from_review
from packages.contracts.models import (
    ChapterMetaContract,
    CharactersContract,
    MemoryGateContract,
    OutlineContract,
    ReviewContract,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "packages" / "contracts" / "schemas"


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


class ContractSchemaTests(unittest.TestCase):
    def test_golden_outline_validates(self) -> None:
        payload = {
            "contract_version": "1.0.0",
            "chapter_goal": "推进主角与反派第一次正面冲突",
            "conflict": "主角必须在救人和保密之间二选一",
            "beats": ["发现异常", "冲突升级", "做出选择"],
            "foreshadowing": ["旧钟楼", "父亲遗留怀表"],
            "ending_hook": "主角收到匿名警告短信",
        }
        model = OutlineContract.model_validate(payload)
        validate(instance=model.model_dump(), schema=_load_schema("outline.schema.json"))

    def test_golden_review_validates(self) -> None:
        payload = {
            "contract_version": "1.0.0",
            "character_consistency_score": 90,
            "world_consistency_score": 92,
            "style_match_score": 88,
            "repetition_issues": [],
            "revision_suggestions": [
                "硬约束检查：must_include 已覆盖：旧钟楼线索",
                "硬约束检查：must_not_include 未触发",
                "硬约束检查：continuity_constraints 无违例",
            ],
        }
        model = ReviewContract.model_validate(payload)
        validate(instance=model.model_dump(), schema=_load_schema("review.schema.json"))

    def test_golden_characters_validates(self) -> None:
        payload = {
            "contract_version": "1.0.0",
            "characters": [
                {
                    "character_id": "char_kurono_001",
                    "canonical_name": "黑野真",
                    "display_name": "黑野真",
                    "aliases": ["阿真"],
                    "merge_status": "CONFIRMED",
                    "role": "主角",
                    "age": 17,
                    "personality": [],
                    "background": [],
                    "abilities": [],
                    "limitations": [],
                    "relationships": {},
                    "motivation": [],
                    "key_memories": [],
                    "story_function": [],
                    "beliefs": [],
                    "ambiguity": [],
                    "identities": [],
                }
            ],
        }
        model = CharactersContract.model_validate(payload)
        validate(instance=model.model_dump(), schema=_load_schema("characters.schema.json"))

    def test_golden_chapter_meta_validates(self) -> None:
        payload = {
            "contract_version": "1.0.0",
            "chapter_id": "chapter_005",
            "kind": "NORMAL",
            "title": "钟房密钥",
            "subtitle": None,
            "volume_id": None,
            "arc_id": None,
            "order_index": 5,
            "status": "GENERATED",
            "summary": "主角从怀表中得到关键线索。",
            "created_at": "2026-03-15T00:00:00Z",
            "updated_at": "2026-03-15T00:00:00Z",
        }
        model = ChapterMetaContract.model_validate(payload)
        validate(instance=model.model_dump(mode="json"), schema=_load_schema("chapter_meta.schema.json"))

    def test_golden_memory_gate_validates(self) -> None:
        payload = {
            "contract_version": "1.0.0",
            "pass": False,
            "issues": ["style_match_score<70"],
            "recommended_action": "REVIEW_MANUALLY",
        }
        model = MemoryGateContract.model_validate(payload)
        validate(
            instance=model.model_dump(mode="json", by_alias=True),
            schema=_load_schema("memory_gate.schema.json"),
        )

    def test_legacy_characters_name_is_mapped(self) -> None:
        legacy = {
            "title": "旧人物设定",
            "characters": [
                {"name": "林砚", "role": "主角", "aliases": ["阿砚"]},
            ],
        }
        normalized = normalize_characters_payload(legacy, strict=False)
        first = normalized["characters"][0]
        self.assertEqual(first["canonical_name"], "林砚")
        self.assertEqual(first["display_name"], "林砚")
        self.assertTrue(first["character_id"].startswith("char_legacy_"))

    def test_title_only_can_build_chapter_meta(self) -> None:
        meta = build_min_chapter_meta(chapter_id="chapter_009", title="临界时刻")
        validated = ChapterMetaContract.model_validate(meta)
        self.assertEqual(validated.chapter_id, "chapter_009")
        self.assertEqual(validated.title, "临界时刻")

    def test_missing_memory_gate_can_be_derived_from_review(self) -> None:
        review = {
            "character_consistency_score": 60,
            "world_consistency_score": 90,
            "style_match_score": 88,
            "repetition_issues": [],
        }
        gate = normalize_memory_gate_from_review(
            review=review,
            min_score=70,
            max_repetition=2,
        )
        self.assertFalse(gate["pass"])
        self.assertEqual(gate["recommended_action"], "REVIEW_MANUALLY")

    def test_review_without_explicit_requirement_checks_fails(self) -> None:
        payload = {
            "character_consistency_score": 90,
            "world_consistency_score": 90,
            "style_match_score": 90,
            "repetition_issues": [],
            "revision_suggestions": ["建议精简一句重复描写。"],
        }
        with self.assertRaises(ValueError):
            normalize_review_payload(payload, strict=True)


if __name__ == "__main__":
    unittest.main()
