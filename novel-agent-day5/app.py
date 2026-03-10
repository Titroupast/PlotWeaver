from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from openai import OpenAI

from config import ARK_API_KEY, ARK_BASE_URL, ARK_MODEL
from prompts import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_TEMPLATE,
    REVIEWER_SYSTEM_PROMPT,
    REVIEWER_USER_TEMPLATE,
    WRITER_SYSTEM_PROMPT,
    WRITER_USER_TEMPLATE,
)
from tools import ToolRunner

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
    memory_context: str,
    style_constraints: str,
    max_retry: int = 1,
) -> Dict[str, Any]:
    user_prompt = PLANNER_USER_TEMPLATE.format(
        previous_chapter=previous_chapter.strip(),
        requirements=requirements.strip(),
        memory_context=memory_context.strip() or "无",
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
    client: OpenAI,
    previous_chapter: str,
    outline: Dict[str, Any],
    memory_context: str,
) -> str:
    outline_json = json.dumps(outline, ensure_ascii=False, indent=2)
    user_prompt = WRITER_USER_TEMPLATE.format(
        previous_chapter=previous_chapter.strip(),
        outline_json=outline_json,
        memory_context=memory_context.strip() or "无",
    )
    return call_chat(client, WRITER_SYSTEM_PROMPT, user_prompt, WRITER_TEMPERATURE)


def generate_review(
    client: OpenAI,
    chapter_text: str,
    character_summary: str,
    world_summary: str,
    max_retry: int = 1,
) -> Dict[str, Any]:
    user_prompt = REVIEWER_USER_TEMPLATE.format(
        chapter_text=chapter_text.strip(),
        character_summary=character_summary.strip() or "无",
        world_summary=world_summary.strip() or "无",
    )
    last_text = ""
    attempts = 1 + max_retry
    for attempt in range(attempts):
        if attempt == 0:
            response = call_chat(client, REVIEWER_SYSTEM_PROMPT, user_prompt, 0.2)
        else:
            fix_prompt = (
                "上一次输出不是合法 JSON。请修复并仅输出合法 JSON 对象，"
                "不要添加任何多余文本。\n\n"
                f"上一次输出：\n{last_text}"
            )
            response = call_chat(client, REVIEWER_SYSTEM_PROMPT, fix_prompt, 0.0)

        last_text = response
        try:
            payload = extract_json_object(response)
            return json.loads(payload)
        except json.JSONDecodeError:
            continue

    raise ValueError("Failed to produce valid review JSON after retry.")


def resolve_input_path(novel_id: str, provided: Optional[Path], filename: str) -> Path:
    if provided is not None:
        return provided
    return INPUTS_DIR / novel_id / filename


def resolve_chapter_path(
    novel_id: str, chapter_id: Optional[str], provided: Optional[Path]
) -> Optional[Path]:
    if provided is not None:
        return provided
    if chapter_id is None:
        return None
    return INPUTS_DIR / novel_id / "chapters" / chapter_id / "chapter.txt"


def resolve_chapter_req_path(novel_id: str, chapter_id: Optional[str]) -> Optional[Path]:
    if chapter_id is None:
        return None
    return INPUTS_DIR / novel_id / "chapters" / chapter_id / "continuation_req.txt"


def extract_keywords(text: str, limit: int = 8) -> List[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,4}", text)
    stopwords = {"这次", "这样", "一个", "这里", "他们", "我们", "你们", "什么", "怎么", "但是"}
    counts: Dict[str, int] = {}
    for token in tokens:
        if token in stopwords:
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0])))
    return [item[0] for item in ranked[:limit]]


def next_chapter_id(chapter_id: str) -> Optional[str]:
    match = re.match(r"chapter_(\d+)$", chapter_id)
    if not match:
        return None
    number = int(match.group(1)) + 1
    return f"chapter_{number:03d}"


def split_title_and_body(text: str) -> Dict[str, str]:
    lines = text.strip().splitlines()
    if not lines:
        return {"title": "## 未命名章节", "body": text.strip()}
    title = lines[0].strip()
    if not title.startswith("## "):
        title = f"## {title}"
    return {"title": title, "body": "\n".join(lines)}


def update_index(index_path: Path, chapter_id: str, title: str, generated: bool = True) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    title_clean = title.replace("##", "").strip()
    suffix = " (generated)" if generated else ""
    line = f"{chapter_id.replace('chapter_', '')}\t{title_clean}{suffix}"

    lines = []
    if index_path.exists():
        lines = [ln.rstrip("\n") for ln in index_path.read_text(encoding="utf-8").splitlines()]

    # Avoid duplicates for the same chapter id
    updated = []
    replaced = False
    for ln in lines:
        if ln.startswith(chapter_id.replace("chapter_", "")):
            updated.append(line)
            replaced = True
        else:
            updated.append(ln)
    if not replaced:
        updated.append(line)

    index_path.write_text("\n".join(updated).strip() + "\n", encoding="utf-8")


def pick_lines_by_keywords(lines: Iterable[str], keywords: List[str], limit: int) -> List[str]:
    picked = []
    for line in lines:
        if any(keyword in line for keyword in keywords):
            picked.append(line.strip())
        if len(picked) >= limit:
            break
    return picked


def summarize_characters(characters_path: Path, keywords: List[str]) -> List[str]:
    if not characters_path.exists():
        return []
    data = json.loads(characters_path.read_text(encoding="utf-8"))
    characters = data.get("characters", [])
    results = []
    for entry in characters:
        name = entry.get("name", "")
        role = entry.get("role", "")
        summary = f"{name}：{role}"
        serialized = json.dumps(entry, ensure_ascii=False)
        if not keywords or any(keyword in serialized for keyword in keywords):
            results.append(summary)
    return results[:6]


def build_review_context(memory_dir: Path) -> Dict[str, str]:
    characters_path = memory_dir / "characters.json"
    world_path = memory_dir / "world_rules.md"

    character_summary = ""
    if characters_path.exists():
        data = json.loads(characters_path.read_text(encoding="utf-8"))
        lines = []
        for entry in data.get("characters", []):
            name = entry.get("name", "")
            role = entry.get("role", "")
            if name:
                lines.append(f"{name}：{role}".strip("："))
        character_summary = "\n".join(lines[:8])

    world_summary = ""
    if world_path.exists():
        lines = [line.strip() for line in world_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        world_summary = "\n".join(lines[:8])

    return {"character_summary": character_summary or "无", "world_summary": world_summary or "无"}


def build_memory_context(
    memory_dir: Path,
    previous_chapter: str,
    requirements: str,
    tool_runner: ToolRunner,
) -> str:
    keywords = extract_keywords(previous_chapter + "\n" + requirements)

    characters_path = memory_dir / "characters.json"
    world_path = memory_dir / "world_rules.md"
    story_path = memory_dir / "story_so_far.md"

    character_lines = summarize_characters(characters_path, keywords)
    world_lines = []
    story_lines = []

    if world_path.exists():
        world_lines = pick_lines_by_keywords(
            [line for line in world_path.read_text(encoding="utf-8").splitlines() if line.strip()],
            keywords,
            limit=5,
        )
    if story_path.exists():
        story_lines = pick_lines_by_keywords(
            [line for line in story_path.read_text(encoding="utf-8").splitlines() if line.strip()],
            keywords,
            limit=5,
        )

    sections = []
    if character_lines:
        sections.append("【人物设定】\n" + "\n".join(character_lines))
    if world_lines:
        sections.append("【世界设定】\n" + "\n".join(world_lines))
    if story_lines:
        sections.append("【剧情摘要】\n" + "\n".join(story_lines))

    if characters_path.exists() or world_path.exists() or story_path.exists():
        sections.append("【记忆来源】\ncharacters.json / world_rules.md / story_so_far.md")

    return "\n\n".join(sections) if sections else "无"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Day 5: review + tools + outline + write.")
    parser.add_argument("--novel-id", default="demo", help="Novel identifier.")
    parser.add_argument("--prev", type=Path, help="Path to prev_chapter.txt.")
    parser.add_argument("--req", type=Path, help="Path to continuation_req.txt.")
    parser.add_argument("--style", type=Path, help="Optional style constraints file.")
    parser.add_argument("--chapter-id", help="Use inputs/<novel_id>/chapters/<id>/chapter.txt.")
    parser.add_argument("--max-retry", type=int, default=1, help="JSON retry count.")
    parser.add_argument("--refresh-memory", action="store_true", help="Rebuild memory files from chapters.")
    parser.add_argument(
        "--only-refresh-memory",
        action="store_true",
        help="Only rebuild memory files and exit.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    novel_id = args.novel_id

    prev_path = resolve_input_path(novel_id, args.prev, "prev_chapter.txt")
    req_path = args.req if args.req is not None else (BASE_DIR / "prompts" / "continuation_req.txt")
    chapter_path = resolve_chapter_path(novel_id, args.chapter_id, None)
    style_path = args.style

    if chapter_path is not None:
        prev_path = chapter_path

    memory_dir = INPUTS_DIR / novel_id / "memory"
    run_log_path = OUTPUTS_DIR / novel_id / "run_log.json"
    tool_runner = ToolRunner(
        build_client(),
        ARK_MODEL,
        memory_dir,
        run_log_path,
        BASE_DIR / "prompts",
        OUTPUTS_DIR / novel_id,
    )

    if args.refresh_memory:
        chapters_root = INPUTS_DIR / novel_id / "chapters"
        chapter_files = sorted(chapters_root.glob("chapter_*/chapter.txt"))
        chapters_text = "\n\n".join(read_text(path) for path in chapter_files)
        if chapters_text:
            tool_runner.build_characters(chapters_text)
            tool_runner.build_world_rules(chapters_text)
            tool_runner.build_story_so_far(chapters_text)

    if args.only_refresh_memory:
        tool_runner.flush()
        print("[Info] Memory refreshed. Exiting as requested.")
        return

    if not prev_path.exists():
        raise FileNotFoundError(f"Missing prev_chapter file: {prev_path}")
    if not req_path.exists():
        raise FileNotFoundError(f"Missing continuation_req file: {req_path}")
    if style_path and not style_path.exists():
        raise FileNotFoundError(f"Missing style constraints file: {style_path}")

    previous_chapter = read_text(prev_path)
    requirements = read_text(req_path)
    style_constraints = read_text(style_path) if style_path else ""


    memory_context = build_memory_context(memory_dir, previous_chapter, requirements, tool_runner)

    client = build_client()

    outline = generate_outline(
        client,
        previous_chapter,
        requirements,
        memory_context,
        style_constraints,
        max_retry=args.max_retry,
    )
    next_id = next_chapter_id(args.chapter_id) if args.chapter_id else None
    if next_id:
        output_dir = OUTPUTS_DIR / novel_id / "chapters" / next_id
    elif args.chapter_id:
        output_dir = OUTPUTS_DIR / novel_id / "chapters" / args.chapter_id
    else:
        output_dir = OUTPUTS_DIR / novel_id

    outline_path = output_dir / "outline.json"
    write_text(outline_path, json.dumps(outline, ensure_ascii=False, indent=2))

    draft = generate_draft(client, previous_chapter, outline, memory_context)
    title_and_body = split_title_and_body(draft)

    if next_id:
        input_next_dir = INPUTS_DIR / novel_id / "chapters" / next_id
        write_text(input_next_dir / "chapter.txt", title_and_body["body"])
        write_text(input_next_dir / "title.txt", title_and_body["title"])
        write_text(input_next_dir / "output.txt", "generated_by=app.py")
        update_index(INPUTS_DIR / novel_id / "chapters" / "index.txt", next_id, title_and_body["title"], True)

    draft_path = output_dir / "chapter.txt" if (args.chapter_id or next_id) else (output_dir / "draft_v4.txt")
    write_text(draft_path, title_and_body["body"])
    if args.chapter_id or next_id:
        write_text(output_dir / "title.txt", title_and_body["title"])

    tool_runner.save_chapter_draft(draft, next_id or args.chapter_id or "draft_v4")
    tool_runner.flush()

    review_ctx = build_review_context(memory_dir)
    review = generate_review(
        client,
        title_and_body["body"],
        review_ctx["character_summary"],
        review_ctx["world_summary"],
    )
    review_path = output_dir / "review.json"
    write_text(review_path, json.dumps(review, ensure_ascii=False, indent=2))

    print(f"[Saved] {outline_path}")
    print(f"[Saved] {draft_path}")
    print(f"[Saved] {review_path}")


if __name__ == "__main__":
    main()
