from __future__ import annotations

import json
from pathlib import Path
from typing import Type

from pydantic import BaseModel

from .models import (
    ChapterMetaContract,
    CharactersContract,
    MemoryGateContract,
    OutlineContract,
    ReviewContract,
)


def write_schema(model: Type[BaseModel], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema = model.model_json_schema()
    output_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    root = Path(__file__).parent / "schemas"
    write_schema(OutlineContract, root / "outline.schema.json")
    write_schema(ReviewContract, root / "review.schema.json")
    write_schema(CharactersContract, root / "characters.schema.json")
    write_schema(ChapterMetaContract, root / "chapter_meta.schema.json")
    write_schema(MemoryGateContract, root / "memory_gate.schema.json")


if __name__ == "__main__":
    main()

