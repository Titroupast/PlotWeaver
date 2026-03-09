from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from openai import OpenAI

from config import ARK_API_KEY, ARK_BASE_URL, ARK_MODEL
from prompts import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_TEMPLATE,
    WRITER_SYSTEM_PROMPT,
    WRITER_USER_TEMPLATE,
)

BASE_DIR = Path(__file__).parent
INPUTS_DIR = BASE_DIR / "inputs"
OUTPUTS_DIR = BASE_DIR / "outputs"

PLANNER_TEMPERATURE = 0.2
WRITER_TEMPERATURE = 0.7


def build_client() -> OpenAI:
    return OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def extract_json_object(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def call_chat(
    client: OpenAI, system_prompt: str, user_prompt: str, temperature: float
) -> str:
    resp = client.chat.completions.create(
        model=ARK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


def generate_outline(
    client: OpenAI,
    previous_chapter: str,
    requirements: str,
    style_constraints: str,
    max_retry: int = 1,
) -> Dict[str, Any]:
    user_prompt = PLANNER_USER_TEMPLATE.format(
        previous_chapter=previous_chapter.strip(),
        requirements=requirements.strip(),
        style_constraints=style_constraints.strip() or "无",
    )

    last_text = ""
    attempts = 1 + max_retry
    for attempt in range(attempts):
        if attempt == 0:
            response = call_chat(
                client, PLANNER_SYSTEM_PROMPT, user_prompt, PLANNER_TEMPERATURE
            )
        else:
            fix_prompt = (
                "上一次输出不是合法 JSON。请修复并仅输出合法 JSON 对象，"
                "不要添加任何多余文本。\n\n"
                f"上一次输出：\n{last_text}"
            )
            response = call_chat(client, PLANNER_SYSTEM_PROMPT, fix_prompt, 0.0)

        last_text = response
        try:
            payload = extract_json_object(response)
            return json.loads(payload)
        except json.JSONDecodeError:
            continue

    raise ValueError("Failed to produce valid JSON outline after retry.")


def generate_draft(
    client: OpenAI, previous_chapter: str, outline: Dict[str, Any]
) -> str:
    outline_json = json.dumps(outline, ensure_ascii=False, indent=2)
    user_prompt = WRITER_USER_TEMPLATE.format(
        previous_chapter=previous_chapter.strip(), outline_json=outline_json
    )
    return call_chat(client, WRITER_SYSTEM_PROMPT, user_prompt, WRITER_TEMPERATURE)


def resolve_input_path(novel_id: str, provided: Optional[Path], filename: str) -> Path:
    if provided is not None:
        return provided
    return INPUTS_DIR / novel_id / filename


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Day 2: outline then write.")
    parser.add_argument("--novel-id", default="demo", help="Novel identifier.")
    parser.add_argument("--prev", type=Path, help="Path to prev_chapter.md.")
    parser.add_argument("--req", type=Path, help="Path to continuation_req.md.")
    parser.add_argument("--style", type=Path, help="Optional style constraints file.")
    parser.add_argument("--max-retry", type=int, default=1, help="JSON retry count.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    novel_id = args.novel_id

    prev_path = resolve_input_path(novel_id, args.prev, "prev_chapter.txt")
    req_path = resolve_input_path(novel_id, args.req, "continuation_req.txt")
    style_path = args.style

    if not prev_path.exists():
        raise FileNotFoundError(f"Missing prev_chapter file: {prev_path}")
    if not req_path.exists():
        raise FileNotFoundError(f"Missing continuation_req file: {req_path}")

    if style_path and not style_path.exists():
        raise FileNotFoundError(f"Missing style constraints file: {style_path}")

    previous_chapter = read_text(prev_path)
    requirements = read_text(req_path)
    style_constraints = read_text(style_path) if style_path else ""

    client = build_client()

    outline = generate_outline(
        client,
        previous_chapter,
        requirements,
        style_constraints,
        max_retry=args.max_retry,
    )
    output_dir = OUTPUTS_DIR / novel_id
    outline_path = output_dir / "outline.json"
    write_text(outline_path, json.dumps(outline, ensure_ascii=False, indent=2))

    draft = generate_draft(client, previous_chapter, outline)
    draft_path = output_dir / "draft_v2.txt"
    write_text(draft_path, draft)

    print(f"[Saved] {outline_path}")
    print(f"[Saved] {draft_path}")


if __name__ == "__main__":
    main()
