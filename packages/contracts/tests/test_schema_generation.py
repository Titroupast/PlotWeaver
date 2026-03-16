from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from packages.contracts.constants import CONTRACT_VERSION
from packages.contracts.generate_schemas import write_schema
from packages.contracts.models import (
    ChapterMetaContract,
    CharactersContract,
    MemoryGateContract,
    OutlineContract,
    ReviewContract,
)


def _load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_files_can_be_generated_and_are_valid_jsonschema(tmp_path: Path) -> None:
    mappings = [
        ("outline.schema.json", OutlineContract),
        ("review.schema.json", ReviewContract),
        ("characters.schema.json", CharactersContract),
        ("chapter_meta.schema.json", ChapterMetaContract),
        ("memory_gate.schema.json", MemoryGateContract),
    ]

    for filename, model in mappings:
        target = tmp_path / filename
        write_schema(model, target)
        schema = _load_schema(target)
        Draft202012Validator.check_schema(schema)
        assert "properties" in schema
        assert "contract_version" in schema["properties"]
        contract_prop = schema["properties"]["contract_version"]
        assert contract_prop.get("default") == CONTRACT_VERSION
